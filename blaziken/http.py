""" Defines the basic class for making HTTP requests. """
# Meta imports
from __future__ import annotations
from typing import TYPE_CHECKING
# Third-party imports
from requests import get as _http_get
from requests import post as _http_post
from requests.exceptions import RequestException
# Project imports
from blaziken.exceptions import InternetError
from blaziken.utils import check_response_error

if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from requests.models import Response
    from typing import Callable


class Http:
    """
    Class for making HTTP requests using default configuration settings, such as timeout.

    :ivar timeout: The default timeout, in seconds, for the HTTP requests.
    """

    def __init__(self, timeout:float=8.0):
        self.timeout = timeout  # in seconds

    def _do_request(self, method:Callable, *args, **kwargs) -> Response:
        """
        Makes an arbitrary HTTP request and checks for errors.

        :raises InternetError: If there is no internet connection available.
        :raises RequestError: If the request contains errors.
        """
        kwargs.setdefault('timeout', self.timeout)
        try:
            response = method(*args, **kwargs)
            check_response_error(response)
            return response
        except RequestException:
            raise InternetError('No internet connection available')

    def get(self, *args, **kwargs) -> Response:
        """
        Makes a HTTP GET request and checks for errors.

        :raises InternetError: If there is no internet connection available.
        :raises RequestError: If the request contains errors.
        """
        return self._do_request(_http_get, *args, **kwargs)

    def post(self, *args, **kwargs) -> Response:
        """
        Makes a HTTP POST request and checks for errors.

        :raises InternetError: If there is no internet connection available.
        :raises RequestError: If the request contains errors.
        """
        return self._do_request(_http_post, *args, **kwargs)
