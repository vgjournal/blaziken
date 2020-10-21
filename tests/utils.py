""" Module with helpful functions to make testing easier. """
# Built-in imports
from enum import Enum
from json import loads as json_loads
from pathlib import Path
# Project imports
from blaziken.meta import Json


RESPONSES_PATH = Path(__file__).parent / 'b2_responses'


class Response:
    """
    Class for simulating the response given by the BackBlazeB2 service.

    :ivar string: The raw json-encoded response.
    :ivar dict: The response parsed as a python dict object.
    """

    def __init__(self, path:Path):
        with open(path, 'r', encoding='utf8') as file_handle:
            self.string = file_handle.read().strip()
            self.dict = json_loads(self.string)


class Responses(Enum):
    """ Enum listing the mock responses from each endpoint of the BackBlazeB2 service. """

    create_bucket = Response(RESPONSES_PATH / 'b2_create_bucket.json')
    get_file_info = Response(RESPONSES_PATH / 'b2_get_file_info.json')
    list_buckets = Response(RESPONSES_PATH / 'b2_list_buckets.json')
    list_files = Response(RESPONSES_PATH / 'b2_list_file_names.json')

    @property
    def json(self) -> Json:
        return self.value.dict
