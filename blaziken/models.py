""" Module for the Model classes used in the object-oriented API. """
# Meta imports
from __future__ import annotations
from typing import TYPE_CHECKING
# Built-in imports
from datetime import datetime
from pathlib import Path
# Project imports
from blaziken import BackBlazeB2
from blaziken.enums import BucketType
from blaziken.enums import FileAction
from blaziken.enums import KeyCapabilities
from blaziken.exceptions import BucketError
from blaziken.exceptions import FileError
from blaziken.exceptions import ResponseError

if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from blaziken.http import Http
    from blaziken.meta import UploadGenerator
    from typing import Any
    from typing import BinaryIO
    from typing import Dict
    from typing import Generator
    from typing import List
    from typing import Optional
    from typing import Union


class B2Objects:
    """ Root class for using the object-oriented API of the library. """

    def __init__(self, account_id:str, app_key:str, auth:bool=False,
                 http:Optional[Http]=None):
        self._api = BackBlazeB2(account_id, app_key, auth, http)

    @property
    def account_id(self) -> str:
        """ Gets the account id associated with the instance. """
        return self._api.account_id

    @property
    def app_key(self) -> str:
        """ Gets the app id associated with the instance. """
        return self._api.app_key

    @property
    def api(self) -> BackBlazeB2:
        return self._api

    def authenticate(self, account_id:str, app_key:str) -> Dict[str, Any]:
        """
        Authenticates (or re-authenticates, if already authenticated) an account.

        IMPORTANT: When authenticating with a non-master application key, use the key's id as the
        account id, otherwise the response will produce a 401 Unauthorized error.

        :param account_id: The account id to be used for authentication, or the key id if
                           authenticating with a non-master application key.
        :param app_key: The secret value of the application key to be used for authentication.
        :returns: A dict with the json-encoded response data.
        """
        return self.api.authenticate(account_id, app_key)

    def key(self, key_id:str) -> Optional[Key]:
        """ Retrieves the data of a single application Key. """
        data = self.api.list_keys(self.api.account_id, 1, key_id).get('keys', [])
        return Key(self._api, data[0]) if data else None

    def keys(self) -> List[Key]:
        """ Lists non-expired application keys. """
        return [Key(self._api, key_info)
                for key_info in self._api.list_keys(self._api.account_id).get('keys', [])]

    def buckets(self) -> List[Bucket]:
        """ Lists all existing buckets in the authenticated account. """
        return [Bucket(self._api, bucket_info)
                for bucket_info in self._api.list_buckets().get('buckets', [])]

    def bucket(self, name:str='', bucket_id:str='') -> Bucket:
        """
        Retrieves a single bucket using its name or id.

        :param name: Retrives the bucket matching the specified name.
        :param bucket_id: Retrives the bucket matching the specified id.
        :returns: A Bucket instance matching the specified bucket.
        :raises BucketError: If no buckets matching the name or id were found.
        """
        if self.api.limited_account:
            return Bucket(self.api,
                          {'bucketName': self.api.bucket_name, 'bucketId': self.api.bucket_id})
        response = self._api.list_buckets(
            bucket_id if bucket_id else None, name if name else None).get('buckets', [])
        if not response:
            raise BucketError(f'No bucket exists with name "{name}" or id "{bucket_id}".')
        return Bucket(self._api, response[0])

    def create_bucket(self, bucket_name:str, private:bool, bucket_info=None, cors_rules=None,
                      lifecycle_rules=None) -> Bucket:
        """
        Creates a new bucket. The bucket name must be unique in the whole BackblazeB2 service.

        :param bucket_name: The name of the bucket. Must be valid and unique.
        :param private: True to make the bucket private, False to make it public.
        :param bucket_info: Unused.
        :param cors_rules: Unused.
        :param lifecycle_rules: Unused.
        :returns: A Bucket instance pointing to the newly-created bucket.
        """
        return Bucket(self._api, self._api.create_bucket(bucket_name, private, bucket_info,
                                                         cors_rules, lifecycle_rules))

    def create_key(self, account_id:str, capabilities:List[KeyCapabilities], key_name:str,
                   bucket_id:str='', prefix:str='', duration:int=0):
        """
        Creates a new application key that might have limited access to the account's data.
        When creating a Key, be sure to save the Key.app_key value. This key is used to
        authenticate the account, and it is only shown during key creation, i.e., it cannot be
        retrieved later. For detailed parameters, see BackBlazeB2.create_key().

        :returns: A Key instance pointing to the newly-created key.
        """
        return Key(self._api, self._api.create_key(account_id, capabilities, key_name, bucket_id,
                                                   prefix, duration))


class Key:
    """
    Represents an application key that gives access to an account features.
    When creating a Key, be sure to save the Key.app_key value. This key is used to authenticate
    the account, and it is only shown during key creation, i.e., it cannot be retrieved later.
    """

    def __init__(self, api:BackBlazeB2, data:Dict[str, Any]):
        self._api = api
        self.id = data.get('applicationKeyId', '')  # pylint: disable = invalid-name
        self.account_id = data.get('accountId')
        self.app_key = data.get('applicationKey', '')
        self.capabilities = [KeyCapabilities(value) for value in data.get('capabilities', [])]
        self.name = data.get('keyName')
        self.prefix = data.get('namePrefix')
        self.options = data.get('options', [])
        expiration = data.get('expirationTimestamp')  # Timestamp response is in milliseconds
        self.expiration = datetime.fromtimestamp(expiration / 1000) if expiration else None
        self.bucket_id = data.get('bucketId')

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}:{self.id}> {self.name}'

    @property
    def api(self) -> BackBlazeB2:
        return self._api

    def delete(self):
        self._api.delete_key(self.id)


class Bucket:
    """ Model representing a Bucket in the BackBlaze B2 service. """

    def __init__(self, api:BackBlazeB2, data:Dict[str, Any]):
        self._api = api
        # 'id' is an exception to the invalid-name rule
        self.id = data.get('bucketId', '')  # pylint: disable = invalid-name
        self.name = data.get('bucketName', '')
        self.info = data.get('bucketInfo', {})
        self.type = BucketType(data.get('bucketType', ''))
        self.cors = data.get('corsRules', [])
        self.life_cycle = data.get('lifecycleRules', [])
        self.options = data.get('options', [])
        self.revision = data.get('revision', -1)
        self._next_files = None
        self._next_params = tuple()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}:{self.id}> {self.name}'

    @property
    def api(self) -> BackBlazeB2:
        return self._api

    def files(self, prefix:str='', delimiter:str=BackBlazeB2.FOLDER_DELIMITER,
              max_files:int=BackBlazeB2.DEFAULT_FILE_COUNT, start_name:str='') -> List[File]:
        """
        List files contained in the bucket.
        Parameters are the same as :func:`~blaziken.api.BackBlazeB2.list_files`.

        :returns: A list containing files matching the specified parameters.
        """
        results = self._api.list_files(prefix, delimiter, max_files, start_name, self.id)
        self._next_files = results.get('nextFileName')
        self._next_params = (prefix, delimiter, max_files) if self._next_files else tuple()
        return [File(self._api, self, file_info) for file_info in results.get('files', [])]

    def more_files(self) -> Generator[List[File], None, None]:
        """
        After calling Bucket.files(), calling Bucket.more_files() will retrieve more files if the
        number of returned files was greater than max_files. If files() is called again before
        more_files(), it will not be possible to retrieve the remaining files of the first call.
        The parameters prefix, delimiter, max_files passed to the files() call will be repeated
        when calling more_files().

        :yields: A list of File objects representing the next set of results.

        :example:

        >>> bucket = B2Objects('account_id', 'app_key').bucket('b2-example-bucket')
        >>> for bucket_file in bucket.list_files('prefix', None, 10):
        >>>     do_stuff(bucket_file)
        >>> while more_files in bucket.more_files():
        >>>     for bucket_file in more_files:
        >>>         do_stuff(bucket_file)

        """
        while True:
            if not self._next_files or not self._next_params:
                break
            more_files = self.files(*self._next_params, self._next_files)
            if not more_files:
                break
            yield more_files

    def all_files(self, prefix:str='', delimiter:Optional[str]=None,
                  max_files:int=BackBlazeB2.DEFAULT_FILE_COUNT, start_name:str=''
                  ) -> Generator[File, None, None]:
        """
        Combines :func:`Bucket.files()` and :func:`Bucket.more_files()` into a single generator
        that yields all files matching the given parameters.
        Parameters are the same as :func:`Bucket.files()` (max_files will be the maximum number of
        files per request, not in total).
        """
        for bucket_file in self.files(prefix, delimiter, max_files, start_name):
            yield bucket_file
        for more_files in self.more_files():
            for bucket_file in more_files:
                yield bucket_file

    def folder(self, name:str, delimiter:Optional[str]=BackBlazeB2.FOLDER_DELIMITER,
               max_files:int=BackBlazeB2.DEFAULT_FILE_COUNT) -> List[File]:
        """
        Lists only the contents of the virtual folder matching the name parameter.
        Sub-folders will be included in the response. If the folder has more files than max_files,
        use :func:`Bucket.more_files()` to list them.

        :param name: The name/path of the folder to have its files listed.
        :param delimiter: The delimiter used in the file names to create/separate virtual folders.
        :param max_files: The number of files
        :returns: A list containing files and folders in the specified folder.
        """
        return self.files(name if name.endswith(delimiter) else f'{name}{delimiter}',
                          delimiter, max_files)

    def file(self, file_id:str='', file_name:str='') -> File:
        """
        Gets a single file from the bucket using either its id or full file name.

        :param file_id: The id of the file to be retrieved.
        :param file_name: The full name of the file to be retrieved.
        :returns: A File instance representing the desired file.
        :raises FileError: If no file matches the specified id or name.
        """
        if file_name:
            try:
                return self.files(max_files=1, start_name=file_name)[0]
            except IndexError:
                raise FileError(f'No file exists with name "{file_name}" in bucket "{self.name}".')
        try:
            return File(self._api, self, self._api.get_file_info(file_id))
        except ResponseError as exc:
            raise FileError(f'No file exists with id "{file_id}" in bucket "{self.name}".') from exc

    def delete(self):
        """ Deletes the bucket. """
        self._api.delete_bucket(self.id)

    def upload_iter(self, file_or_path:Union[str, Path, BinaryIO], file_name:str='',
                    append_filename:bool=False, file_size:int=0) -> UploadGenerator:
        """
        Uploads a file to the bucket, yield the result of each part's upload.
        Parameters are the same as BackBlazeB2.upload.
        """
        return self._api.upload(file_or_path, file_name, append_filename, file_size, self.id)

    def upload(self, file_or_path:Union[str, Path, BinaryIO], file_name:str='',
               append_filename:bool=False, file_size:int=0) -> File:
        """ Uploads a file to the bucket. Parameters are the same as BackBlazeB2.upload. """
        return File(self.api, self, list(self._api.upload(
            file_or_path, file_name, append_filename, file_size, self.id))[-1][0])


class File:
    """
    Model representing a File in the BackBlaze B2 service.
    To allow third-parties to download a file from a private bucket, an authorization token is
    required. Obtaining the auth token is handled automatically.

    :cvar AUTH_TOKEN_DURATION: The time (in seconds) until an auth token expires. Default: 8 hours.
    """

    AUTH_TOKEN_DURATION = 8 * 60 * 60  # 8 hours

    def __init__(self, api, bucket:Bucket, data:Dict[str, Any]):
        self._api = api
        self.bucket = bucket
        self.id = data.get('fileId', '')  # pylint: disable = invalid-name
        self.name = data.get('fileName', '')
        self.size = data.get('contentLength', -1)
        self.md5 = data.get('contentMd5', '')
        self.sha1 = data.get('contentSha1', '')
        self.content_type = data.get('contentType', '')
        self.timestamp = data.get('uploadTimestamp', -1)
        self.extra = data.get('fileInfo', {})
        self.action = FileAction(data.get('action', ''))

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}:{self.id[:5]}...{self.id[-5:]}> {self.name}'

    @property
    def extension(self) -> str:
        return Path(self.name).suffix

    @property
    def base_name(self) -> str:
        return Path(self.name).name

    @property
    def api(self) -> BackBlazeB2:
        return self._api

    @property
    def url(self) -> str:
        return f'{self.api.download_url}/file/{self.bucket.name}/{self.name}'

    @property
    def is_folder(self) -> bool:
        return self.action == FileAction.folder if self.action else not bool(self.id)

    def download_url(self, token_duration:int=AUTH_TOKEN_DURATION) -> str:
        if self.bucket.type == BucketType.public:
            return self._api.download_url_path(self.name, bucket_name=self.bucket.name)
        auth_token = self._api.get_download_auth(self.name, token_duration, self.bucket.id)
        return self._api.download_url_path(self.name, auth_token, self.bucket.name)

    def download(self, save_path:Path) -> Path:
        path = save_path / self.base_name if save_path.is_dir() else save_path
        self._api.download_file(self.download_url(), path, )
        return path

    def delete(self):
        self._api.delete_file(self.id, self.name)
