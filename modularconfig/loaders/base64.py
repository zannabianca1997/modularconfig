from typing import Dict
from base64 import b64decode
from binascii import Error as b64Error

from modularconfig.errors import LoadingError, OptionParseError

from .bool import load as load_boolean

name = "base64"
aliases = ["b64"]


def load(text: str, options: Dict[str, str]) -> bytes:
    """Load the text as a base64 object"""
    parsed_options = {}
    if "altchars" in options:
        parsed_options["altchars"] = options["altchars"]
    if "validate" in options:
        if options["validate"]:  # a value was specified
            try:
                parsed_options["validate"] = load_boolean(options["validate"], {})
            except LoadingError as e:
                raise OptionParseError(*e.args) from None
        else:
            parsed_options["validate"] = True  # use as a flag
    try:
        return b64decode(text, **parsed_options)
    except b64Error as e:
        raise LoadingError("Can't decode base64") from e