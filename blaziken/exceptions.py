""" Module containing all errors raised by the library. """


class BlazeError(Exception):
    """ Base class for all BackBlazeB2 exceptions. """


class RequestError(BlazeError):
    """ Exception raised when an error is found in the request before it is sent. """


class ResponseError(BlazeError):
    """ Exception raised when the request is successful but the Response returns an error. """


class InternetError(BlazeError):
    """ Exception raised when there an internet problem, such as no connection. """


class ObjectError(BlazeError):
    """ Errors related to the object-oriented interface operations. """


class BucketError(ObjectError):
    """ Error related to operations on Bucket model objects. """


class B2KeyError(ObjectError):
    """ Error related to operations on Key model objects. KeyError is a default exception. """


class FileError(ObjectError):
    """ Error related to operations on File model objects. """
