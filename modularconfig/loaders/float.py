from typing import Dict
from modularconfig.errors import LoadingError

names = ["float", "real"]


def load(text: str, options: Dict[str, str]) -> float:
    """Try to load a number as a float"""
    text = text.strip()
    try:
        return float(text)
    except ValueError as e:
        raise LoadingError("Can't convert to a float") from e