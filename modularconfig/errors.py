class ConfigNotFoundError(KeyError):
    """The requested config is missing"""


class ConfigFileNotFoundError(ConfigNotFoundError, FileNotFoundError):
    """The requested config point to a file that doesn't exist"""


class LoadingError(ValueError):
    """There was a problem in the loading of the configs"""


class LoaderMissingError(LoadingError):
    """A file requested a loader that is missing"""


class DisabledLoaderError(LoadingError):
    """A file requested a loader that's disabled"""
