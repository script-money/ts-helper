class SeleniumException(Exception):
    """
    Selenium base exception. Handled at the outermost level.
    All other exception types are subclasses of this exception type.
    """


class RegionNotAvaliableException(Exception):
    """
    RegionNotAvaliable exception.
    """


class HttpxRequestException(Exception):
    """
    Httpx client post exception
    """
