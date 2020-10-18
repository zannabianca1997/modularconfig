from typing import Dict
from modularconfig.errors import LoadingError

from json import loads, JSONDecodeError

names = ["json"]


def load(text: str, options: Dict[str, str]) -> object:
    """Load the text as a json object"""
    try:
        return loads(text)
    except JSONDecodeError as e:
        raise LoadingError("Can't decode json") from e