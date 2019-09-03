"""AEMET: Custom exception classes used by AEMET component"""


class AemetException(Exception):
    pass


class InvalidApiKey(AemetException):
    raise ValueError("Invalid api key error")


class NotFound(AemetException):
    pass


class TooManyRequests(AemetException):
    pass


class NoResponseException(AemetException):
    raise ValueError("No respose received")

