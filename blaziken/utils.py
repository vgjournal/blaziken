""" Utility functions to be reused throughout the application. """
# Meta imports
from __future__ import annotations
from typing import TYPE_CHECKING
# Built-in imports
from hashlib import sha1
from json import loads as json_loads
from math import ceil
from pathlib import Path
from re import match
from sys import version_info as version
# Project imports
from blaziken.exceptions import ResponseError
from blaziken.exceptions import RequestError
from blaziken.constants import FIVE_GB
from blaziken.constants import FIVE_MB
from blaziken.constants import HUNDRED_MB

if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from requests.models import Response
    from typing import Any
    from typing import BinaryIO
    from typing import Dict
    from typing import Tuple
    from typing import Union


def valid_bucket_name(name:str) -> bool:
    """
    Validates the name of a bucket.
    A bucket name must have between 6 and 50 alfanumeric characters (or -), must not start with
    'b2-' and be globally unique. This method does not check for uniqueness.

    :param name: The bucket name to be validated.
    :returns: True if the bucket name appears to be valid, False otherwise.
    """
    return not name.startswith('b2-') and match(r'^[\da-zA-Z\-]{6,50}$', name) is not None


def check_response_error(response:Response):
    """
    Checks the Http response object for errors.

    :param response: The Http response object to be checked for errors.
    :raises RequestError: If the response contains errors.
    """
    if response.status_code >= 400:
        raise RequestError(response.text)


def check_b2_errors(data:Dict[str, Any], message:str):
    """
    Checks if the response produced any errors.

    :param data: The data returned by the BackBlazeB2 web service.
    :param message: The message included in the exception raised if an error is detected.
    :raises ResponseError: If the response had an error.
    """
    if data.get('status', 0) >= 400:  # Successful requests do not have the 'status' key
        raise ResponseError(message)


def python_version_string() -> str:
    """ Gets the python version in the format X.Y.Z. """
    return f'{version.major}.{version.minor}.{version.micro}'


def file_sha1(file_handle:BinaryIO, block_size:int=65536) -> str:
    """
    Gets the sha1 hash of a file reading block by block.

    :param file_handle: An file opened with binary reading mode.
    :param block_size: The maximum size (in bytes) of each block read from the file.
    :returns: The sha1 hexdigest of the file.
    """
    sha1_hash = sha1()
    while True:
        data = file_handle.read(block_size)
        if not data:
            break
        sha1_hash.update(data)
    return sha1_hash.hexdigest()


def upload_parts_count(file_path_or_size:Union[str, Path, int],
                       part_size:int=HUNDRED_MB) -> Tuple[int, int, int]:
    """
    Gets the number of upload parts of a file. Maximum number of parts is 10000 (around 48GB with
    5MB parts), and parts must have between 5MB and 5GB (except the last part).

    :param file_path_or_size: The file size, in bytes, or the path to the file in the file system.
    :param part_size: The size of each upload part, in bytes. Each upload will use at least this
                      amount of memory (if the file is larger than the part size). Minimum is 5MB.
    :returns: A 3-tuple containing (total file size, number of parts, part size), sizes in bytes.
    """
    if part_size < FIVE_MB or part_size > FIVE_GB:
        raise ValueError("Part size cannot be less than 5MB or more than 5GB")
    size = file_path_or_size if isinstance(file_path_or_size, int) \
        else Path(file_path_or_size).stat().st_size
    parts = ceil(size / part_size)
    return (size, parts, part_size,)
