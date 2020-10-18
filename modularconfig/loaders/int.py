from typing import Dict
from modularconfig.errors import LoadingError

names = ["int", "integer"]


def load(text: str, options: Dict[str, str]) -> int:
    """Try to load a number as a int.py"""
    text = text.strip()
    try:
        return int(text)
    except ValueError as e:
        raise LoadingError("Can't convert to an integer") from e