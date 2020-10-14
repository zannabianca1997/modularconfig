from contextlib import contextmanager
from logging import getLogger
from os import PathLike, scandir, getcwd
from os.path import split, exists, isfile, join, isdir, normpath
from typing import Dict, List, Callable, Any, Iterable, Iterator, Tuple

import json

logger = getLogger(__name__)

# loaded objects
_configs: Dict[PathLike, object] = {}

# functions capable of loading objects from a text
loaders: List[Tuple[str, Callable[[str], Any]]] = [
    ("json", json.loads),
    ("text", str)
]

# config base directory
config_directory: PathLike = getcwd()


class ConfigNotFoundError(KeyError):
    """The requested config is missing"""


class ConfigFileNotFoundError(ConfigNotFoundError, FileNotFoundError):
    """The requested config point to a file that doesn't exist"""


class LoadingError(ValueError):
    """There was a problem in the loading of the configs"""


class LoaderMissingError(LoadingError):
    """A file requested a loader that is missing"""


def _split_attributes(config: PathLike):
    """Return the file containing the config (first part of path) and the remaining attributes

    >>> _split_attributes("/path/to/file/foo/bar"))  #doctest: +SKIP
    ('/path/to/file', ('foo', 'bar'))
    """
    attributes = []
    while not exists(config):  # until we don't find a true file
        config, attrib = split(config)
        attributes.append(attrib)
    if not isfile(config):  # the path didn't contain a file
        raise ConfigFileNotFoundError(join(config, attributes[-1]))
    return config, tuple(reversed(attributes))


def _load_string(text: str):
    """Load a python object from the file content
    Try all the loaders from loaders in order

    >>> _load_string('{"answer": 42, "question": "6x9"}')  # json
    {'answer': 42, 'question': '6x9'}
    >>> _load_string("Value")  # load directly as string
    'Value'

    A particular loader can be specified, if invalid errors are propagated
    >>> _load_string("#type:text\\n{'data':'this is not a json'}")
    "{'data':'this is not a json'}"
    >>> _load_string("#type: json \\n InvalidJson")
    Traceback (most recent call last):
      ...
    json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)

    Logs the failed tries with the logging module, with level logging.DEBUG
    """
    if text.startswith("#type:"):  # a loader is specified
        splits = text.split("\n", maxsplit=1)  # taking away first line
        if len(splits) == 1:  # only one line, loaders is given but data is empty
            data_type = splits[0]
            text = ""
        else:
            data_type, text = splits
        data_type = data_type[6:].strip()  # getting the given type
        for name, loader in loaders:
            if data_type == name:
                data = loader(text)  # leave all the eventual exceptions to propagate
                break
        else:
            raise LoaderMissingError(data_type)
    else:
        for name, loader in loaders:
            try:
                data = loader(text)
            except ValueError:  # loader didn't work
                continue  # proceed to next loader
            else:  # loaded worked
                break  # stop trying, data was found
        else:  # no loader worked
            # usually this is never throw thanks to text loader
            raise LoadingError("None of the loaders worked, try to add type specification to see the error")
    return data


def reload_file(config_file: PathLike):
    """Load (or reload) the file in the memory

    >>> import tempfile; tmp_file = tempfile.mktemp()
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42}')
    14
    >>> reload_file(tmp_file)
    >>> _configs[tmp_file]
    {'answer': 42}
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42, "question":"6x9"}')
    32
    >>> reload_file(tmp_file)  # will reload the file
    >>> _configs[tmp_file]
    {'answer': 42, 'question': '6x9'}
    """
    with open(config_file) as conf:
        text = conf.read()
    data = _load_string(text)
    _configs[config_file] = data


def ensure_file(config_file: PathLike):
    """Ensure a file is loaded

    >>> import tempfile; tmp_file = tempfile.mktemp()
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42}')
    14
    >>> ensure_file(tmp_file)
    >>> _configs[tmp_file]
    {'answer': 42}
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42, "question":"6x9"}')
    32
    >>> ensure_file(tmp_file)  # won't reload the file
    >>> _configs[tmp_file]
    {'answer': 42}
    """
    if config_file not in _configs:
        reload_file(config_file)



def _get_attr(obj: object, attrs: Iterable[str]):
    """Recursively get attributes from an object.

    >>> dct = {"baz":{"bar":42}}
    >>> _get_attr(dct, ("baz", "bar"))  # equivalent to dct["baz"]["bar"]
    42

    KeyError is raised if an attribute isn't found
    >>> _get_attr(dct, ("baz","foo", "bac"))
    Traceback (most recent call last):
      ...
    KeyError: ('baz', 'foo')

    """

    def _recursive_get(found_obj: object, remaining_attrs: Iterator[str]):
        try:
            attr = next(remaining_attrs)  # the attribute we need to open at this level at this level
        except StopIteration:
            return found_obj  # we got to the end of the path
        child_obj = found_obj[attr]
        try:
            return _recursive_get(child_obj, remaining_attrs)
        except LookupError as e:  # an attribute wasn't found
            e.args = (attr,) + e.args  # adding the full path to the exception
            raise
    return _recursive_get(obj, iter(attrs))


def _load_dir(dir_name: PathLike):
    """Load a directory as dict

    example: if we have this direcory tree
    Foo
        -Baz
            -goo.txt
            -gee.json
        -bar.txt

    then
    >>> _load_dir("Foo")  # doctest: +SKIP
    {'Baz':{'goo.txt': 'goo.txt content', 'gee.json': {'content': 'content'}}, 'bar.txt': 'bar.txt content'}
    """
    loaded = {}
    for entry in scandir(dir_name):
        entry_path = join(dir_name, entry.name)
        if entry.is_dir():
            loaded[entry.name] = _load_dir(entry_path)  # recursive load subdirectories
        else:
            ensure_file(entry_path)  # load the file if missing
            loaded[entry.name] = _configs[entry_path]  # recover the loaded file
    return loaded


@contextmanager
def open_config_directory(relative_config_directory: PathLike):
    """Temporanely set a new config directory. Can be relative to the old"""
    global config_directory
    old_dir = config_directory
    change_config_directory(relative_config_directory)
    yield
    config_directory = old_dir  # returning back


def change_config_directory(relative_config_directory: PathLike):
    """Change the config directory. Can be relative to the old"""
    global config_directory
    config_directory = normpath(join(config_directory, relative_config_directory))


def get(config: PathLike):
    """Return the requested config

    >>> from tempfile import NamedTemporaryFile; from json import dump; from os.path import join
    >>> with NamedTemporaryFile(mode="w", delete=False) as fil:
    ...     dump({"bar":"foo"}, fil)
    ...     filename = fil.name
    >>> get(join(filename, "./bar"))
    'foo'
    """
    config = normpath(join(config_directory, config))  # make it relative to the prefix (still permit absolutes)
    # first we check if is a directory
    if exists(config) and isdir(config):
        return _load_dir(config)
    else:  # we are entering inside a file
        filename, attrs = _split_attributes(config)
        ensure_file(filename)  # load the file if missing
        try:
            return _get_attr(_configs[filename], attrs)  # get the requested attributes and return
        except KeyError as e:
            raise ConfigNotFoundError(join(filename, e.args)) from e