from typing import Dict
from modularconfig.errors import LoadingError

name = "none"
aliases = ["null"]


def load_none(text: str, options: Dict[str, str]) -> None:
    """If the lowered text is empty, 'none' or 'null' None is returned"""
    text = text.strip().lower()
    if text not in {"", "none", "null"}:
        raise LoadingError("text is not empty, 'none' or 'null'")
    return None
