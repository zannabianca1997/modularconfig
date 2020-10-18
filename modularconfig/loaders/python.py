from typing import Dict
from modularconfig.errors import LoadingError

name = "python"


def dangerous_load(text: str, options) -> Dict[str, object]:
    """Load the globals defined in a python script
    >>> dangerous_load("a=5\\nb=4")
    {'a': 5, 'b': 4}
    """
    script_vars = {}
    try:
        exec(text, script_vars)
    except Exception as e:
        raise LoadingError("An exception has arise in the loading of the python script") from e
    del script_vars["__builtins__"]  # deleting buitins
    return script_vars
