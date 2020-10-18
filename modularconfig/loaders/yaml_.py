from typing import Dict
from modularconfig.errors import LoadingError, LoaderMissingError

name = "yaml"

try:
    import yaml
except ImportError as e:
    def load(text: str, options: Dict[str, str]) -> object:
        """Dummy load function if yaml is not installed"""
        raise LoaderMissingError("Yaml is not installed on the system") from e
    dangerous_load = load
else:
    def load(text: str, options: Dict[str, str]) -> object:
        """Safely load a subset of yaml"""
        try:
            docs = list(yaml.safe_load_all(text))  # only safe features
        except yaml.YAMLError as e:
            raise LoadingError("Can't parse YAML") from e  # must use ValueError
        if len(docs) == 0:
            return {}
        if len(docs) == 1:
            return docs[0]  # only one document
        return docs  # leave as a list of documents

    def dangerous_load(text: str, options: Dict[str, str]) -> object:
        """Load the full yaml specification. This can execute arbitrary code"""
        try:
            docs = list(yaml.full_load_all(text))  # load the full yaml
        except yaml.YAMLError as e:
            raise LoadingError("Can't parse YAML") from e  # must use ValueError
        if len(docs) == 0:
            return {}
        if len(docs) == 1:
            return docs[0]  # only one document
        return docs  # leave as a list of documents
