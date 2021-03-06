from typing import Dict
from modularconfig.errors import LoadingError

name = "bool"
aliases = ["boolean"]


def load(text: str, options: Dict[str, str]) -> bool:
    """If the lowered text is 'true' or 'false' the appropriate boolean is returned"""
    text = text.strip().lower()
    if text in {"true", "yes", "on"}:
        return True
    if text in {"false", "no", "off"}:
        return False
    raise LoadingError("Can't determine boolean value")