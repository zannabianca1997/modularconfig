import binascii
from io import BytesIO
from locale import getpreferredencoding
from typing import List, Callable, Any, Union, Dict, TextIO, Tuple, Iterator

import json
from base64 import b64decode

from modularconfig.errors import LoaderMissingError, LoadingError, DisabledLoaderError, OptionParseError

try:
    import yaml
except ImportError:
    yaml = None

dangerous_loaders = {
    "yaml_full_loader": False,
    "python": False
}


def load_int(text: str, **options) -> int:
    """Try to load a number as a int"""
    text = text.strip()
    try:
        return int(text)
    except ValueError as e:
        raise LoadingError("Can't convert to an integer") from e


def load_float(text: str, **options) -> float:
    """Try to load a number as a float"""
    text = text.strip()
    try:
        return float(text)
    except ValueError as e:
        raise LoadingError("Can't convert to a float") from e


def load_complex(text: str, **options) -> complex:
    """Try to load a number as a complex"""
    text = text.strip()
    try:
        return complex(text)
    except ValueError as e:
        raise LoadingError("Can't convert to a complex") from e


def load_number(text: str, **options) -> Union[int, float, complex]:
    """Try to load a number as a int, then as a float, then as a complex"""
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


def load_boolean(text: str, **options) -> bool:
    """If the lowered text is 'true' or 'false' the appropriate boolean is returned"""
    text = text.strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise LoadingError("Can't determine boolean value")


def load_none(text: str, **options) -> None:
    """If the lowered text is empty, 'none' or 'null' None is returned"""
    text = text.strip().lower()
    if text not in {"", "none", "null"}:
        raise LoadingError("text is not empty, 'none' or 'null'")
    return None

def load_json(text: str, **options) -> object:
    """Load the text as a json object"""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LoadingError("Can't decode json") from e

def load_yaml(text: str, **options) -> object:
    """If yaml is present will try to load text"""
    if not yaml:
        raise LoaderMissingError("Yaml is not installed, can't be used in a file")
    try:
        if dangerous_loaders["yaml_full_loader"]:
            docs = list(yaml.full_load_all(text))  # load the full yaml
        else:
            docs = list(yaml.safe_load_all(text))  # only safe features
    except yaml.YAMLError as e:
        raise LoadingError("Can't parse YAML") from e  # must use ValueError
    if len(docs) == 0:
        return {}
    if len(docs) == 1:
        return docs[0]  # only one document
    return docs  # leave as a list of documents


def load_python(text: str, **options) -> Dict[str, object]:
    """Load the globals defined in a python script
    >>> dangerous_loaders["python"] = True
    >>> load_python("a=5\\nb=4")
    {'a': 5, 'b': 4}
    """
    if not dangerous_loaders["python"]:
        raise DisabledLoaderError("Python loader is disabled")
    script_vars = {}
    exec(text, script_vars)
    del script_vars["__builtins__"]  # deleting buitins
    return script_vars


def load_text(text: str, **options) -> str:
    """Load directly the text"""
    return text


def load_base64(text: str, **options) -> bytes:
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
    except binascii.Error as e:
        raise LoadingError("Can't decode base64") from e

# disponible loaders
loaders: Dict[str, Callable[[str], Any]] = {
    # dict types
    "json": load_json,
    "yaml": load_yaml,
    "python": load_python,
    # number types
    "int": load_int,
    "integer": load_int,
    "float": load_float,
    "real": load_float,
    "complex": load_complex,
    "number": load_number,
    # booleans
    "bool": load_boolean,
    "boolean": load_boolean,
    # none loaders
    "null": load_none,
    "none": load_none,
    # general string loader
    "text": load_text,
    # base64 loader, for small binary pieces. If you need big binary data, they should not be in the configs
    "base64": load_base64
}

# if no type is specified this loaders will be tried in this order
auto_loader: List[str] = [
    "number",
    "bool",
    "none",
    "json",
    "python",
    "text"
]

if yaml:
    auto_loader[auto_loader.index("json")] = "yaml"  # substituting json with is superset yaml


def expand_token(tokens: Iterator[Union[str, object]], token_str: str, token_obj: object) \
    -> Iterator[Union[str, object]]:
    """
    Expand a token from strings

    >>> list(expand_token(iter(["hello for a friend of a friend"]), "friend", 3))
    ['hello for a ', 3, ' of a ', 3, '']
    """
    for token in tokens:
        if isinstance(token, str):  #splitting
            subtokens = token.split(token_str)
            yield subtokens[0]
            for subtoken in subtokens[1:]:
                yield token_obj
                yield subtoken
        else:
            yield token  # do not touch


def collapse_token(tokens: Iterator[Union[str, object]], token_str: str, token_obj: object) \
    -> Iterator[Union[str, object]]:
    """
    inverse the token expansion

    >>> list(collapse_token(iter(['hello for a ', 3, ' of a ', 3, '']), "friend", 3))
    ['hello for a friend of a friend']

    it collapse strings too
    >>> list(collapse_token(iter(["it ", "collapse ", "strings"]), "friend", 3))
    ['it collapse strings']
    """
    cum_string = ""
    for token in tokens:
        if isinstance(token, str):
            cum_string += token
        elif token == token_obj:
            cum_string += token_str
        else:
            if cum_string:  # we found an untouch token, cleaning cumulative string
                yield cum_string
                cum_string = ""
            yield token
    if cum_string:  # yielding last string
        yield cum_string


def split_options(datatype: str) -> Tuple[str, Dict[str, str]]:
    """Split the options from the datatype

    >>> split_options("text ")
    ('text', {})
    >>> split_options("text:encoding=latin1")
    ('text', {'encoding': 'latin1'})
    >>> split_options('  loader : a = 5; b = long ass string  ; flag')
    ('loader', {'a': ' 5', 'b': ' long ass string  ', 'flag': ''})
    >>> split_options(
    ...     "loader : surprise =can use escape sequences \\\\=, \\\\;, \\\\n, \\\\\\\\t"
    ... )[1]["surprise"]
    'can use escape sequences =, ;, \\n, \\\\t'
    """
    datatype_and_opt = datatype.split(":", maxsplit=1)
    if len(datatype_and_opt) == 1:  # no options
        return datatype.strip(), {}
    datatype, options = datatype_and_opt
    EQUAL_TOKEN, SEPARE_TOKEN = object(), object()
    ESCAPED_EQUAL, ESCAPED_SEPARE = object(), object()
    # first we separe our escaped sequences
    explicit_escapes = expand_token(
        expand_token(
            iter([options]), "\\=", ESCAPED_EQUAL
        ), "\\;", ESCAPED_SEPARE
    )
    # then we escape our true separators
    explicit_escapes = expand_token(
        expand_token(
            explicit_escapes, "=", EQUAL_TOKEN
        ), ";", SEPARE_TOKEN
    )
    # finally we recollapse our escaped sequence
    tokenized_options = list(collapse_token(
        collapse_token(
            explicit_escapes, "=", ESCAPED_EQUAL
        ), ";", ESCAPED_SEPARE
    ))
    # now tokenized_options is a list of strings, EQUAL_TOKEN, SEPARE_TOKEN
    opt_name, opt_content = "", ""
    reading_name = True  # false when reading content
    parsed_opt = {}
    for token in tokenized_options:
        if isinstance(token, str):
            if reading_name:
                opt_name += token
            else:
                opt_content += token
        elif token == EQUAL_TOKEN:
            if not reading_name:
                raise OptionParseError(f"Double equal sign in {datatype}")
            reading_name = False  # start reading content
        elif token == SEPARE_TOKEN:  # came to an end of option
            opt_name = opt_name.strip()
            if not opt_name:
                raise OptionParseError(f"No options name in {datatype}")
            parsed_opt[opt_name] = opt_content
            # resetting parser
            opt_name, opt_content = "", ""
            reading_name = True
    # parsing last option
    opt_name = opt_name.strip()
    if not opt_name:
        raise OptionParseError(f"No options name in {datatype}")
    parsed_opt[opt_name] = opt_content
    # escaping standard escape sequences
    for opt in parsed_opt:
        parsed_opt[opt] = parsed_opt[opt].encode("utf-8").decode("unicode_escape")
    return datatype.strip(), parsed_opt


# todo: maybe the file descriptor should be passed to the loaders? this will permit them to read the file sequentially
def load_file(file: BytesIO):
    """Load a python object from the file content
    Try all the loaders from loaders in order
    >>> from io import BytesIO
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
        data_type, options = split_options(
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
            data = loaders[data_type](text, **options)
        else:
            raise LoaderMissingError(data_type)

    else:  # no loader specified, try to autodetect
        encoding = getpreferredencoding()
        try:
            text = (head + file.read()).decode(encoding)
        except UnicodeDecodeError as e:
            raise LoadingError(f"Cant decode file using {encoding}") from e
        for name in auto_loader:
            try:
                data = loaders[name](
                    text
                )
            except ValueError:  # loader didn't work
                continue  # proceed to next loader
            else:  # loaded worked
                break  # stop trying, the data was succesfully loaded
        else:  # no loader worked
            # usually this is never throw thanks to text loader
            raise LoadingError("None of the loaders worked, try to add type specification to see the error")
    return data
