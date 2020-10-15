from typing import List, Tuple, Callable, Any, Union, Dict

import json
from base64 import b64decode
from warnings import warn

try:
    import yaml
except ImportError:
    yaml = None
else:
    yaml_use_full_loader = False


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
                raise ValueError("Can't convert to a number") from None


def boolean(text: str) -> bool:
    """If the lowered text is 'true' or 'false' the appropriate boolean is returned"""
    text = text.strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError("Can't determine boolean value")


def none(text: str) -> None:
    """If the lowered text is empty, 'none' or 'null' None is returned"""
    text = text.strip().lower()
    if text not in {"", "none", "null"}:
        raise ValueError("text is not empty, 'none' or 'null'")
    return None

def load_yaml(text: str) -> object:
    """If yaml is present will try to load text"""
    if not yaml:
        raise ValueError("Yaml is not installed, can't be used in a file")
    try:
        if yaml_use_full_loader:
            docs = list(yaml.full_load_all(text))  # load the full yaml
        else:
            docs = list(yaml.safe_load_all(text))  # only safe features
    except yaml.YAMLError as e:
        raise ValueError("Can't parse YAML") from e  # must use ValueError
    if len(docs) == 0:
        return {}
    if len(docs) == 1:
        return docs[0]  # only one document
    return docs  # leave as a list of documents




# disponible loaders
loaders: Dict[str, Callable[[str], Any]] = {
    # dict types
    "json": json.loads,
    "yaml": load_yaml,
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
    "text"
]

if yaml:
    auto_loader[auto_loader.index("json")] = "yaml"  # substituting json with is superset yaml
