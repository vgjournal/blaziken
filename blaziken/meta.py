""" Module with meta values, such as custom type annotation classes. """
from typing import Any
from typing import Dict
from typing import Generator
from typing import Tuple


Json = Dict[str, Any]
UploadGenerator = Generator[Tuple[Json, int, int], None, None]
