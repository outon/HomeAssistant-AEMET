"""AEMET: Custom exception classes used by AEMET component"""


class AemetException(Exception):
    pass


class InvalidApiKey(AemetException):
    pass


class NotFound(AemetException):
    pass


class TooManyRequests(AemetException):
    pass


class NoResponseException(AemetException):
    pass

