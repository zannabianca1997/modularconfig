from typing import Dict, List, Tuple
from json import loads as load_json, JSONDecodeError
import configparser

from modularconfig.errors import LoadingError, OptionParseError
from .bool import load as load_boolean


name = "ini"
aliases = ["inifile", "winconfig"]


def parse_tuple_of_strings(text:str) -> Tuple[str]:
    try:
        # using json to load list
        parsed = load_json(text)
    except JSONDecodeError as e:
        raise OptionParseError("Can't parse delimiters as a pair of string") from e
    # checking if type is right
    if not isinstance(parsed, list):
        raise OptionParseError("Can't parse delimiters as a pair of string")
    if not all(isinstance(obj, str) for obj in parsed):
        raise OptionParseError("Can't parse delimiters as a pair of string")
    return tuple(parsed)

#todo: write doctests
def load(text: str, options: Dict[str, str]) -> configparser.ConfigParser:
    """Import from a ini file, generate a configparser.ConfigParser instance that holds the loaded data
    ConfigParser support indexing, so users can change config_dir even to the section

    Supported options are:
        allow_no_value
        delimiters
        comment_prefixes
        inline_comment_prefixes
        strict
        empty_lines_in_values
        default_section
        interpolation: none, basic, extended
    """
    parsed_opt = {}
    for bool_opt in ("allow_no_value", "strict", "empty_lines_in_values"):
        if bool_opt in options:
            parsed_opt[bool_opt] = load_boolean(
                options[bool_opt], {}
            )
    for str_tuple_opt in ("delimiters", "comment_prefixes", "inline_comment_prefixes"):
        if str_tuple_opt in options:
            parsed_opt[str_tuple_opt] = parse_tuple_of_strings(options[str_tuple_opt])
    if "default_section" in options:
        parsed_opt["default_section"] = options["default_section"]

    if "interpolation" in options:
        interpolation = options["interpolation"].strip().lower()
        if interpolation == "none":
            interpolation = None
        elif interpolation == "basic":
            interpolation = configparser.BasicInterpolation
        elif interpolation == "extended":
            interpolation = configparser.ExtendedInterpolation
        else:
            raise OptionParseError(f"Unrecognized interpolation setting {interpolation}")
        parsed_opt["interpolation"] = interpolation

    ini = configparser.ConfigParser(**parsed_opt)
    try:
        ini.read_string(text)
    except configparser.Error as e:
        raise LoadingError("Can't load ini file") from e
    return ini



