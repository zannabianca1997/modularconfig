from typing import Dict
from modularconfig.errors import LoadingError

name = "complex"


def load(text: str, options: Dict[str, str]) -> complex:
    """Try to load a number as a complex"""
    text = text.strip()
    try:
        return complex(text)
    except ValueError as e:
        raise LoadingError("Can't convert to a complex") from e