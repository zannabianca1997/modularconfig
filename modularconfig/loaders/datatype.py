from typing import Iterator, Union, Tuple, Dict

from modularconfig.errors import OptionParseError

name = "datatype"

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
    """Inverse the token expansion

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


def load(datatype: str, options: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """Split the options from the datatype

    >>> load("text ", {})
    ('text', {})
    >>> load("text:encoding=latin1", {})
    ('text', {'encoding': 'latin1'})
    >>> load('  loader : a = 5; b = long ass string  ; flag', {})
    ('loader', {'a': ' 5', 'b': ' long ass string  ', 'flag': ''})
    >>> load(
    ...     "loader : surprise =can use escape sequences \\\\=, \\\\;, \\\\n, \\\\\\\\t", {}
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