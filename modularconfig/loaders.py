from typing import List, Callable, Any, Union, Dict, TextIO

import json
from base64 import b64decode

from modularconfig.errors import LoaderMissingError, LoadingError, DisabledLoaderError

try:
    import yaml
except ImportError:
    yaml = None

dangerous_loaders = {
    "yaml_full_loader": False,
    "python": False
}


def number(text: str) -> Union[int, float, complex]:
    """Try to load a number as a int, then as a float, then as a complex"""
    text = text.strip()
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            try:
                return complex(text)
            except ValueError:
                raise LoadingError("Can't convert to a number") from None


def boolean(text: str) -> bool:
    """If the lowered text is 'true' or 'false' the appropriate boolean is returned"""
    text = text.strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise LoadingError("Can't determine boolean value")


def none(text: str) -> None:
    """If the lowered text is empty, 'none' or 'null' None is returned"""
    text = text.strip().lower()
    if text not in {"", "none", "null"}:
        raise LoadingError("text is not empty, 'none' or 'null'")
    return None


def load_yaml(text: str) -> object:
    """If yaml is present will try to load text"""
    if not yaml:
        raise LoaderMissingError("Yaml is not installed, can't be used in a file")
    try:
        if dangerous_loaders["yaml_full_loader"]:
            docs = list(yaml.full_load_all(text))  # load the full yaml
        else:
            docs = list(yaml.safe_load_all(text))  # only safe features
    except yaml.YAMLError as e:
        raise LoadingError("Can't parse YAML") from e  # must use ValueError
    if len(docs) == 0:
        return {}
    if len(docs) == 1:
        return docs[0]  # only one document
    return docs  # leave as a list of documents


def load_python(text: str) -> Dict[str, object]:
    """Load the globals defined in a python script
    >>> dangerous_loaders["python"] = True
    >>> load_python("a=5\\nb=4")
    {'a': 5, 'b': 4}
    """
    if not dangerous_loaders["python"]:
        raise DisabledLoaderError("Python loader is disabled")
    script_vars = {}
    exec(text, script_vars)
    del script_vars["__builtins__"]  # deleting buitins
    return script_vars


# disponible loaders
loaders: Dict[str, Callable[[str], Any]] = {
    # dict types
    "json": json.loads,
    "yaml": load_yaml,
    "python": load_python,
    # number types
    "int": int,
    "integer": int,
    "float": float,
    "real": float,
    "complex": complex,
    "number": number,
    # booleans
    "bool": boolean,
    "boolean": boolean,
    # none loaders
    "null": none,
    "none": none,
    # general string loader
    "text": str,
    # base64 loader, for small binary pieces. If you need big binary data, they should not be in the configs
    "base64": b64decode
}

# if no type is specified this loaders will be tried in this order
auto_loader: List[str] = [
    "number",
    "bool",
    "none",
    "json",
    "python",
    "text"
]

if yaml:
    auto_loader[auto_loader.index("json")] = "yaml"  # substituting json with is superset yaml


# todo: maybe the file descriptor should be passed to the loaders? this will permit them to read the file sequentially
def load_file(file: TextIO):
    """Load a python object from the file content
    Try all the loaders from loaders in order
    >>> from io import StringIO
    >>> load_file(StringIO('{"answer": 42, "question": "6x9"}'))  # json
    {'answer': 42, 'question': '6x9'}
    >>> load_file(StringIO("Value"))  # load directly as string
    'Value'

    A particular loader can be specified, if invalid errors are propagated
    >>> load_file(StringIO("#type:text\\n{'data':'this is not a json'}"))
    "{'data':'this is not a json'}"
    >>> load_file(StringIO("#type: json \\n InvalidJson"))
    Traceback (most recent call last):
      ...
    json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)

    Logs the failed tries with the logging module, with level logging.DEBUG
    """
    head = file.read(6)
    if head == "#type:":  # a loader is specified
        data_type = file.readline().strip()
        if data_type in loaders:
            data = loaders[data_type](
                file.read()
            )
        else:
            raise LoaderMissingError(data_type)
    else:  # no loader specified, try to autodetect
        text = head + file.read()
        for name in auto_loader:
            try:
                data = loaders[name](
                    text
                )
            except ValueError:  # loader didn't work
                continue  # proceed to next loader
            else:  # loaded worked
                break  # stop trying, data was found
        else:  # no loader worked
            # usually this is never throw thanks to text loader
            raise LoadingError("None of the loaders worked, try to add type specification to see the error")
    return data
