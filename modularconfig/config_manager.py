from contextlib import contextmanager
from logging import getLogger
from pathlib import Path, PurePath
from typing import Dict, Iterator, Union, overload, Set, List

from modularconfig.errors import ConfigNotFoundError, ConfigFileNotFoundError
from modularconfig.loaders import load_file

logger = getLogger(__name__)

# loaded objects:
# a tree mocking the filesystem starting from _common_configs_path
_common_configs_path: Union[Path, None] = None
_configs: Union[Dict[str, object], None] = None

_loaded_paths: Set[Path] = set()

# config base directory
_config_directory: Path = Path.cwd()


# --- Path Management ---

def _split_real_file(config: PurePath) -> Path:
    """Return the file or directory containing the config (first part of path) and the remaining attributes

    >>> from tempfile import NamedTemporaryFile
    >>> with NamedTemporaryFile() as fil:
    ...     print(_split_real_file(PurePath(fil.name, "foo/bar")) == Path(fil.name))
    True

    if the path refere to a directory the directory is loaded
    >>> from tempfile import TemporaryDirectory
    >>> with TemporaryDirectory() as dir:
    ...     print(_split_real_file(PurePath(dir)) == Path(dir))
    True

    Directories can't contain values if not inside files:
    >>> with TemporaryDirectory() as dir:
    ...     try:
    ...         _split_real_file(PurePath(dir, "foo/bar"))
    ...     except ConfigFileNotFoundError:
    ...         print(True)
    True
    """
    existing_file = Path(config)
    if existing_file.exists() and existing_file.is_dir():
        return existing_file
    while not existing_file.exists():  # until we don't find a true file, or directory
        existing_file = existing_file.parent
    if existing_file.is_file():
        return existing_file
    raise ConfigFileNotFoundError(f"{config} do not refere to any file")


def _split_config_attributes(config: PurePath) -> PurePath:
    """Return the attributes from _common_configs_path


    >>> _split_config_attributes(_common_configs_path.joinpath("foo/bar"))  #doctest: +SKIP
    PurePosixPath('foo/bar')
    """
    return config.relative_to(_common_configs_path)


def _relative_to_config_directory(config):
    config = _config_directory.joinpath(config).resolve()  # make it relative to the prefix (still permit absolutes)
    return config


@overload
def _common_path(path: Path, *paths: Path) -> Path:
    ...


@overload
def _common_path(path: PurePath, *paths: PurePath) -> PurePath:
    ...


def _common_path(path, *paths):
    """Find the longest common path

    >>> _common_path(PurePath("/etc/base"), PurePath("/etc/common"))
    PurePosixPath('/etc')
    """
    common_path = path.anchor
    if not all(common_path == other_path.anchor for other_path in paths):
        raise OSError("The paths have different anchors")
    common_path = PurePath(common_path)
    for i, part in enumerate(path.parts):
        if not all(other_path.parts[i] == part for other_path in paths):
            break  # we come to the splitting
        common_path /= part  # add to common path
    assert all(common_path in other_path.parents for other_path in paths), \
        "Found common path is not parent of some path"
    return common_path


def _rebase(new_common_config_path: Path) -> None:
    """Change the _common_config_path and adapt _config in accord to the new base.
     Can only go up in the directory tree"""
    global _configs, _common_configs_path
    assert new_common_config_path in _common_configs_path.parents, "Rebase can go only up in the directory tree"
    while _common_configs_path != new_common_config_path:
        _configs = {
            _common_configs_path.name: _configs
        }
        _common_configs_path = _common_configs_path.parent


# --- File Loading ---


def _load_path(config_file: Path, reload: bool):
    """Load (or reload) the file/directory in the memory

    >>> import tempfile; tmp_file = tempfile.mktemp()
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42}')
    14
    >>> get(tmp_file)["answer"]
    42
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 54}')
    14
    >>> _load_path(Path(tmp_file), reload=False)
    >>> get(tmp_file)["answer"]
    42
    >>> _load_path(Path(tmp_file), reload=True)
    >>> get(tmp_file)["answer"]
    54
    """
    global _loaded_paths, _common_configs_path, _configs

    def recursive_load_path(config_file: Path):
        """Recursive reload all files"""
        if (not reload) and (config_file in _loaded_paths):
            return  # this path is already loaded
        config_attributes = _split_config_attributes(config_file)
        if config_file.is_file():
            with open(config_file) as fil:
                data = load_file(fil)
            _set_attr(_configs, config_attributes, data)
        else:
            assert config_file.is_dir(), "There are existing paths that are neither files or directories?"
            # _set_attr(_configs, config_attributes, {})  # create empty dir
            # no empty dir is created, they will be done if a file is generated inside their sub-tree
            for child in config_file.iterdir():
                recursive_load_path(child)  # recursive load

    assert config_file.exists(), "This function should be called only on existing paths"
    if _configs is None:  # first loading
        if config_file.is_dir():
            _common_configs_path = config_file
        else:
            _common_configs_path = config_file.parent  # the path is always a directory, so the file can be any file
        _configs = {}
    elif _common_configs_path not in config_file.parents:
        _rebase(_common_path(config_file, _common_configs_path))  # moving so it can include the new configs
    if (not reload) and _loaded_paths.intersection(config_file.parents):
        return  # is already inside a loaded path (one of his parents was loaded)
    recursive_load_path(config_file)
    _loaded_paths = set(
        path for path in _loaded_paths
        if path not in config_file.parents  # select only the one that wasn't loaded
    )
    _loaded_paths.add(config_file)  # signing this path as loaded


# --- Recursive Get and Set ---

def _get_attr(obj: object, attrs: PurePath):
    """Recursively get attributes from an object.

    >>> dct = {"baz":{"bar":42}}
    >>> _get_attr(dct, PurePath("baz/bar"))  # equivalent to dct["baz"]["bar"]
    42

    KeyError is raised if an attribute isn't found
    >>> _get_attr(dct, PurePath("baz/foo/bac"))
    Traceback (most recent call last):
      ...
    KeyError: PurePosixPath('baz/foo')

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

    try:
        return _recursive_get(obj, iter(attrs.parts))
    except LookupError as e:
        e.args = (PurePath(*e.args),)
        raise


def _set_attr(obj: object, attrs: PurePath, value: object):
    """Recursively set attributes to an object.

    >>> dct = {"baz":{"bar":42}}
    >>> _set_attr(dct, PurePath("baz/bar"), 12)  # equivalent to dct["baz"]["bar"] = 12
    >>> dct["baz"]["bar"]
    12

    KeyError is raised if an attribute that is not the last isn't found
    >>> _get_attr(dct, PurePath("baz/foo/bac"))
    Traceback (most recent call last):
      ...
    KeyError: PurePosixPath('baz/foo')

    """

    def _recursive_set(found_obj: object, remaining_attrs: List[str]):
        attr = remaining_attrs.pop(0)  # the attribute we need to open at this level at this level
        if len(remaining_attrs) == 0:  # we arrived at the end
            found_obj[attr] = value
            return
        if attr not in found_obj:
            found_obj[attr] = {}  # creating parent dirs as needed
        child_obj = found_obj[attr]
        try:
            _recursive_set(child_obj, remaining_attrs)
        except LookupError as e:  # an attribute wasn't found
            e.args = (attr,) + e.args  # adding the full path to the exception
            raise

    try:
        _recursive_set(obj, list(attrs.parts))
    except LookupError as e:
        e.args = (PurePath(*e.args),)
        raise


# --- End User Entry Points ---

@contextmanager
def using_config_directory(relative_config_directory: Union[str, PurePath]):
    """Temporanely set a new config directory. Can be relative to the old"""
    global _config_directory
    old_dir = _config_directory
    set_config_directory(relative_config_directory)
    yield
    _config_directory = old_dir  # returning back


def set_config_directory(relative_config_directory: Union[str, PurePath]):
    """Change the config directory. Can be relative to the old"""
    global _config_directory
    _config_directory = _relative_to_config_directory(relative_config_directory)

def get_config_directory():
    """Return the config directory"""
    return _config_directory


def ensure(config_file: Union[Path, str, bytes], reload: bool = False):
    """Load (or reload) the file/directory in the memory

    >>> import tempfile; tmp_file = tempfile.mktemp()
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 42}')
    14
    >>> get(tmp_file)["answer"]
    42
    >>> with open(tmp_file, "w") as out:
    ...     out.write('{"answer": 54}')
    14
    >>> ensure(tmp_file)
    >>> get(tmp_file)["answer"]
    42
    >>> ensure(tmp_file, reload=True)
    >>> get(tmp_file)["answer"]
    54
    """
    _load_path(_relative_to_config_directory(config_file), reload)


def get(config: Union[str, PurePath]):
    """Return the requested config

    >>> from tempfile import NamedTemporaryFile; from json import dump; from os import remove
    >>> with NamedTemporaryFile(mode="w", delete=False) as fil:
    ...     dump({"bar":"foo"}, fil)
    ...     filename = fil.name
    >>> get(PurePath(filename, "./bar"))
    'foo'
    >>> remove(filename)
    """
    config = _relative_to_config_directory(config)
    _load_path(_split_real_file(config), reload=False)  # ensure the file is loaded
    try:
        return _get_attr(_configs, _split_config_attributes(config))
    except LookupError as e:
        raise ConfigNotFoundError(f"Can't find the config {e.args[0]}") from e
