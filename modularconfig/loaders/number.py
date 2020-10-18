from typing import Dict, Union
from modularconfig.errors import LoadingError

name = "number"
aliases = ["num"]


def load(text: str, options: Dict[str, str]) -> Union[int, float, complex]:
    """Try to load a number as a int.py, then as a float, then as a complex"""
    text = text.strip()
    try:
        return int(text)
    except ValueError as int_err:
        try:
            return float(text)
        except ValueError as float_err:
            try:
                return complex(text)
            except ValueError as complex_err:
                raise LoadingError("Can't convert to a number") from Exception(int_err, float_err, complex_err)