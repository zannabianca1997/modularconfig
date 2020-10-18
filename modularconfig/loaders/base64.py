from typing import Dict
from base64 import b64decode
from binascii import Error as b64Error

from modularconfig.errors import LoadingError

from .bool import load as load_boolean

name = "base64"
aliases = ["b64"]


def load(text: str, options: Dict[str, str]) -> bytes:
    """Load the text as a base64 object"""
    if "altchars" in options:
        altchars = options["altchars"]
    else:
        altchars = None
    if "validate" in options:
        if options["validate"]:  # a value was specified
            validate = load_boolean(options["validate"])
        else:
            validate = True  # use as a flag
    else:
        validate = False
    try:
        return b64decode(text, altchars=altchars, validate=validate)
    except b64Error as e:
        raise LoadingError("Can't decode base64") from e