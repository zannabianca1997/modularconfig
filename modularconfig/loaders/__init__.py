from io import BytesIO
from locale import getpreferredencoding
from pathlib import Path
from importlib import import_module
from typing import List, Callable, Any, Dict


from modularconfig.errors import LoaderMissingError, LoadingError, DisabledLoaderError
from modularconfig.loaders.datatype import load as load_datatype

from logging import getLogger
logger = getLogger(__name__)

dangerous_loaders: Dict[str, bool] = {}
loaders: Dict[str, Callable[[str, Dict[str, str]], Any]] = {}


def register_loader(loader, use_dangerous: bool = False):
    """Add a loader to the disponible ones.

    Loader must have:
    -A "name" attribute, of type str
    -At least one of "load" or "dangerous_load" of type Callable[[str, Dict[str, str]], object]

    Optionally loader can define a "aliases" list, that are equivalent names under wich the loader will be called

    If "dangerous_load" is disponible a flag will be setted in "dangerous_loaders" to the value of "use_dangerous".
    If the flag is false only the safe method will be used, otherwise the dangerous will become the default.
    If no method is possible a DisabledLoaderError will be raised

    The loader will be usable by prefixing the files with "#type: <"name" or "alias"> : ...options... \n".
    The appropriate load function will be called with the file content as the first argument and options as the second.
    If the file is not loadable a LoadingError should be raised.
    """
    global loaders, dangerous_loaders

    if not hasattr(loader, "name"):
        raise TypeError(f"{loader} do not define a name")
    if not (hasattr(loader, "load") or hasattr(loader, "dangerous_load")):
        raise TypeError(f"{loader} do not define any load function")

    if hasattr(loader, "dangerous_load"):
        dangerous_loaders[loader.name] = use_dangerous  # creating the flag
        if hasattr(loader, "load"):
            # creating a function that choose between the two loading
            def load_func(text: str, options: Dict[str, str]):
                if dangerous_loaders[loader.name]:
                    return loader.dangerous_load(text, options)
                else:
                    return loader.load(text, options)
            load_func.__doc__ = f"Load function for type {loader.name}\n" \
                                "\n" \
                                f"If dangerous_loaders['{loader.name}'] is True:\n" \
                                "\n" \
                                f"{loader.dangerous_load.__doc__}\n" \
                                "\n" \
                                "otherwise:\n" \
                                "\n" \
                                f"{loader.load.__doc__}\n"
        else:
            # safeguarding the usage of the dangerous load
            def load_func(text: str, options: Dict[str, str]):
                if dangerous_loaders[loader.name]:
                    return loader.dangerous_load(text, options)
                else:
                    raise DisabledLoaderError(f"'{loader.name}' loader is disabled. "
                                              f"Set dangerous_loaders['{loader.name}'] to True to enable")
            load_func.__doc__ = f"{loader.dangerous_load.__doc__}\n" \
                                f"\n" \
                                f"Usable only if dangerous_loaders['{loader.name}'] is True"
    else:
        load_func = loader.load  # only safe loading is there

    logger.info(f"Adding {loader.name} to the loaders")
    aliases = [loader.name]
    if hasattr(loader, "aliases"):
        aliases.extend(loader.aliases)
    for alias in aliases:
        loaders[alias] = load_func


for file_name in Path(__file__).parent.glob("*.py"):
    if file_name.name == "__init__.py":
        continue  # skip this file
    logger.info(f"Loading {file_name.stem}")
    register_loader(
        import_module(f"modularconfig.loaders.{file_name.stem}")
    )


# if no type is specified this loaders will be tried in this order
auto_loaders: List[str] = [
    "number",
    "bool",
    "none",
    "yaml",  # if not installed will use the dummy loader
    "json",
    "python",  # disabled by default
    "text"
]

# checking that all the default loader are ready
for name in auto_loaders:
    if name not in loaders:
        raise LoaderMissingError(
            f"Loader {name} is missing from source files"
        )
del name


def load_file(file: BytesIO):
    """Load a python object from the file content
    Try all the loaders from loaders in order
    >>> load_file(BytesIO(b'{"answer": 42, "question": "6x9"}'))  # json
    {'answer': 42, 'question': '6x9'}
    >>> load_file(BytesIO(b"Value"))  # load directly as string
    'Value'

    A particular loader can be specified, if invalid errors are propagated
    >>> load_file(BytesIO(b"#type:text\\n{'data':'this is not a json'}"))
    "{'data':'this is not a json'}"
    >>> load_file(BytesIO(b"#type: json \\n InvalidJson"))
    Traceback (most recent call last):
      ...
    modularconfig.errors.LoadingError: Can't decode json

    Logs the failed tries with the logging module, with level logging.DEBUG
    """
    head = file.read(6)
    if head == "#type:".encode("utf-8"):  # a loader is specified?
        data_type, options = load_datatype(
            file.readline().decode("utf-8")[:-1]  # options encoding is utf-8, indexing to strip the newline
        )
        # detect encoding
        if "encoding" in options:
            encoding = options["encoding"].strip()
        else:
            encoding = getpreferredencoding()
        # if an encoding is specified, use that
        try:
            text = file.read().decode(encoding)
        except LookupError as e:
            raise LoadingError(f"Unknown encoding {encoding}") from e
        except UnicodeDecodeError as e:
            raise LoadingError(f"Cant decode file using {encoding}") from e
        # load data
        if data_type in loaders:
            data = loaders[data_type](text, options)
        else:
            raise LoaderMissingError(data_type)

    else:  # no loader specified, try to autodetect
        encoding = getpreferredencoding()
        try:
            text = (head + file.read()).decode(encoding)
        except UnicodeDecodeError as e:
            raise LoadingError(f"Cant decode file using {encoding}") from e
        exceptions = []
        for name in auto_loaders:
            try:
                data = loaders[name](
                    text, {}
                )
            except LoadingError as e:  # loader didn't work
                exceptions.append(e)
                continue  # proceed to next loader
            else:  # loaded worked
                break  # stop trying, the data was succesfully loaded
        else:  # no loader worked
            # usually this is never throw thanks to text loader
            raise LoadingError("None of the loaders worked") from Exception(*exceptions)
    return data
