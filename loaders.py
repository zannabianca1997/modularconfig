from typing import List, Tuple, Callable, Any, Union, Dict

import json
from base64 import b64decode

try:
    import yaml
except ImportError:
    yaml = None


def number(num: str) -> Union[int, float, complex]:
    """Try to load a number as a int, then as a float, then as a complex"""
    try:
        return int(num)
    except ValueError:
        try:
            return float(num)
        except ValueError:
            try:
                return complex(num)
            except ValueError:
                raise ValueError(f"Can't convert {num} to a number") from None


def boolean(text: str) -> bool:
    text = text.strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"Can't determine boolean value of {text}")


def none(text: str) -> None:
    text = text.strip().lower()
    if text not in {"", "none", "null"}:
        raise ValueError("Type none should be used only with empty config")
    return None


# disponible loaders
loaders: Dict[str, Callable[[str], Any]] = {
    # dict types
    "json": json.loads,
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
if yaml:
    loaders["yaml"] = yaml.safe_load

# if no type is specified this loaders will be tried in this order
auto_loader: List[str]
if not yaml:
    auto_loader = [
        "json",
        "number",
        "bool",
        "none",
        "text"
    ]
else:
    auto_loader = [
        "number",
        "bool",
        "none",
        "yaml",  # yaml is a json superset, and can load almost all text
        "text"  # it would be surprising to get there
    ]