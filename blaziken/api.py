"""
Module with BackBlaze B2 WebService API integration.

`B2 Docs <https://www.backblaze.com/b2/docs/>`_.

.. note::

    The hard limit for single-part file uploads is 5GB, multi-part can be from 5MB (each part)
    to 10TB (total).

 """
# Meta imports
from __future__ import annotations
from typing import TYPE_CHECKING
# Built-in imports
from hashlib import sha1
from json import loads as json_loads
from pathlib import Path
from urllib.parse import quote
# Third-party imports
from requests.auth import HTTPBasicAuth
# Project imports
from blaziken import __project__
from blaziken import __version__
from blaziken.constants import FIVE_GB
from blaziken.constants import FIVE_MB
from blaziken.constants import HUNDRED_MB
from blaziken.enums import Endpoints
from blaziken.exceptions import BlazeError
from blaziken.exceptions import RequestError
from blaziken.http import Http
from blaziken.utils import check_b2_errors
from blaziken.utils import python_version_string
from blaziken.utils import upload_parts_count
from blaziken.utils import valid_bucket_name

if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from blaziken.enums import KeyCapabilities
    from blaziken.meta import Json
    from blaziken.meta import UploadGenerator
    from requests.models import Response
    from typing import Any
    from typing import BinaryIO
    from typing import Dict
    from typing import List
    from typing import Optional
    from typing import Tuple
    from typing import Union


# https://www.backblaze.com/b2/docs/integration_checklist.html


class BackBlazeB2():
    """
    Class that manages files and authentication on BackBlaze's B2 service.
    To find out the structure of the JSON-encoded responses, check B2's documentation:
    https://www.backblaze.com/b2/docs/

    Class constants:

    :cvar BUCKET_NAME_MAX_SIZE: The maximum size of the name of a bucket.
    :cvar BUCKET_NAME_MIN_SIZE: The minimum size of the name of a bucket.
    :cvar BUCKET_TYPE_PRIVATE: String defining that a bucket is private.
    :cvar BUCKET_TYPE_PUBLIC: String defining that a bucket is public.
    :cvar FOLDER_DELIMITER: Default delimiter for virtual folders.
    :cvar MAX_LIST_FILES: Absolute maximum of files able to be retrieved in a single request.
    :cvar DEFAULT_FILE_COUNT: Default number of files to be retrieved in a single request.

    Instance variables:

    :ivar account_id: The id of the account.
    :ivar app_key: A key for accessing the API.
    :ivar api_url: The URL provided by the B2 authentication service to access the API.
    :ivar auth_token: The authentication token returned by the B2 authentication service.
    :ivar download_url: The file download URL provided by the B2 authentication service.
    :ivar upload_url: The file upload URL provided by the B2 authentication service.
    :ivar upload_token: The upload token provided by the B2 authentication service.
    :ivar delimiter: The delimiter used to mark directory paths in the B2 service.
    :ivar _bucket_id: The id of the bucket to which the upload token is related to.
    :ivar _bucket_name: The name of the bucket to which the upload token is related to.
    :ivar _prefix: Prefix to be prefixed to all files, restricts access to only files
                   with the same prefix.
    :ivar _http: The Http class used to make HTTP requests.
    :ivar _useragent: The User-Agent header sent in HTTP requests to the B2 service.
    :ivar _limited_account: True indicates that the current account is limited to certain buckets.
    :ivar _capabilities: List of capabilities (permissions) of the current account.
    :ivar _part_size: The minimum part size for large file uploads, in bytes.
    """

    API_VERSION = '/b2api/v2'
    BASE_URL = f'https://api.backblazeb2.com{API_VERSION}'
    # Constants
    BUCKET_NAME_MAX_SIZE = 50
    BUCKET_NAME_MIN_SIZE = 6
    BUCKET_TYPE_PRIVATE = 'allPrivate'
    BUCKET_TYPE_PUBLIC = 'allPublic'
    FOLDER_DELIMITER = '/'
    MAX_LIST_FILES = 10000
    DEFAULT_FILE_COUNT = 100

    def __init__(self, account_id:Optional[str]=None, app_key:Optional[str]=None, auth:bool=False,
                 http:Optional[Http]=None):
        """
        :param account_id: The backblaze account id.
        :param app_key: The API master key.
        :param auth: True to authenticate during initialization, False to do it manually later.
        :param http: An Http object for making HTTP requests.
        """
        self.account_id = account_id
        self.app_key = app_key
        self.api_url:Optional[str] = None
        self.auth_token:Optional[str] = None
        self.download_url:Optional[str] = None
        self.upload_url:Optional[str] = None
        self.upload_token:Optional[str] = None
        self.delimiter = self.FOLDER_DELIMITER
        self._bucket_id:Optional[str] = None
        self._bucket_name:Optional[str] = None
        self._prefix:str = ''
        self._http = http if http else Http()
        self._useragent = f'{__project__}/{__version__}+python/{python_version_string()}'
        self._limited_account = False
        self._capabilities = []
        self._part_size = HUNDRED_MB
        if auth:
            self.authenticate()

    @property
    def is_authenticated(self) -> bool:
        """ Check if the user is authenticated to the B2 service (required for most operations). """
        return self.auth_token is not None

    @property
    def bucket_id(self) -> str:
        """ Gets the id of the currently-selected bucket, if any. """
        return self._bucket_id

    @property
    def bucket_name(self) -> str:
        """ Gets the name of the currently-selected bucket, if any. """
        return self._bucket_name

    @property
    def capabilities(self) -> List[str]:
        """ Gets the list of capabilities (permissions) of the currently-authenticated user. """
        return self._capabilities

    @property
    def limited_account(self) -> bool:
        """ Checks if the account has permission to use a single, specific bucket. """
        return self._limited_account

    @property
    def part_size(self) -> int:
        """ Gets the size (in bytes) for each part of a large upload. """
        return self._part_size

    # region Utility methods
    def _ensure_auth(self):
        """
        Raises an exception if the user is not authenticated.

        :raises RequestError: If the user is not authenticated.
        """
        if not self.is_authenticated:
            raise RequestError(
                'User is not authenticated. Use BackBlazeB2.authenticate() to authenticate.')

    def _headers(self) -> Dict[str, str]:
        """
        Gets the default header dict.

        :returns: A dict with the 'Authorization' and 'Content-Type' headers set.
        """
        return {
            'Authorization': self.auth_token,
            'Content-Type': 'application/json',
            'User-Agent': self._useragent,
        }

    def _base_params(self) -> Dict[str, str]:
        """
        Gets the default body parameters.

        :returns: A dict with the 'accountId' parameter set.
        """
        return {'accountId': self.account_id}

    def _make_url(self, url:str) -> str:
        """ Builds the URL to the B2 API endpoint. """
        return f'{self.api_url}{self.API_VERSION}{url}'

    def prefix(self, append_slash:bool=True) -> str:
        """
        Gets the currently-set file prefix. The prefix is set automatically on limited accounts.

        :param append_slash: True to append a forward slash / to the prefix. Does not adds
                             additional slashes if the prefix already ends with a slash.
        :returns: The current prefix.
        """
        return '{}{}'.format(
            self._prefix, '/' if append_slash and not self._prefix.endswith('/') else '')

    def download_url_path(self, file_name:str, auth_token:str='', bucket_name:str='') -> str:
        """
        Builds the URL to a file.

        :param file_name: The name of the file in the backblaze service.
        :param auth_token: The file's download authorization token. Required for private files.
        :param bucket_name: The name of the bucket where the file is. If empty, will try to use the
                            currently-set bucket.
        :returns: The file download URL.
        :raises ValueError: If the name of the bucket is empty and no bucket is set.
        """
        if not bucket_name and not self.bucket_name:
            raise ValueError('Bucket name not provided nor a bucket was previously selected.')
        return '{base_url}/file/{bucket}/{file_name}{auth}'.format(
            base_url=self.download_url, bucket=bucket_name if bucket_name else self.bucket_name,
            file_name=quote(file_name), auth=f'?Authorization={auth_token}' if auth_token else '')

    def append_filename(self, source_name:str, append_name:str) -> str:
        """ Appends a name to a base name separating them with the configured delimiter. """
        return '{}{}{}'.format(source_name, '' if source_name.endswith(self.delimiter)
                               else self.delimiter, append_name)

    def _upload_file_gen(self, *args, **kwargs) -> UploadGenerator:
        """
        Calls BackBlazeB2.upload_file() and returns a generator.
        This exists so that the various "upload" shortcut methods have the same return type.

        :returns: The file-uploading generator.
        :yields: A 3-tuple containing (upload response, part number, total part count). The part
                 number starts at 1, and if the upload is successfull, the final tuple will have
                 part number 0 and the response will contain the finalized file data.
        """
        yield (self.upload_file(*args, **kwargs), 0, 1)
    # endregion

    # region Configuration methods
    def set_part_size(self, size:int):
        """
        Sets the minimum part size (in bytes) for large uploads. Must be at least 5MB
        and at most 5GB. Default is 100MB (backblaze's recommendation).

        :raises ValueError: If the size is less than 5MB or more than 5GB.
        """
        if size < FIVE_MB or size > FIVE_GB:
            raise ValueError("Part size cannot be less than 5MB or more than 5GB")
        self._part_size = size

    def set_user_agent(self, user_agent:str):
        """ Sets the user agent for the requests. A default user agent is set at initialization. """
        self._useragent = user_agent

    def set_prefix(self, prefix:str=''):
        """
        Sets the prefix to be used when uploading and downloading files.
        Set to empty string to remove auto-prefixing.
        """
        self._prefix = prefix

    def set_delimiter(self, delimiter:str=FOLDER_DELIMITER):
        """
        Sets the character to be used as folder delimiter on file names.  Set to None to disable.

        :param delimiter: The character value to be set as the delimiter.
        """
        self.delimiter = delimiter

    def set_bucket(self, bucket_name:str) -> str:
        """
        Sets the active bucket for the instance.

        :param bucket_name: The name of the bucket to be set as active.
        :returns: The id of the new active bucket.
        :raises RequestError: If not authenticated or does not have permission to list buckets.
        :raises BlazeError: If the bucket does not exist.
        """
        self._ensure_auth()
        buckets = self.list_buckets(bucket_name=bucket_name)
        if not buckets['buckets']:
            raise BlazeError('Bucket ({bucket_name}) does not exist')
        self._bucket_id = buckets['buckets'][0]['bucketId']
        self._bucket_name = bucket_name
        return self._bucket_id
    # endregion

    # region B2 Api methods
    def authenticate(self, account_id:Optional[str]=None, app_key:Optional[str]=None) -> Json:
        """
        Authenticates (or re-authenticates, if already authenticated) an account.
        If the "account_id" and "app_key" attributes were already set in the constructor, it's not
        necessary to specify them again. Specifying them will re-authenticate the account.

        IMPORTANT: When authenticating with a non-master application key, use the key id as the
        account id, otherwise the response will produce a 401 Unauthorized error.

        :param account_id: The account id to be used for authentication, or the key id if
                           authenticating with a non-master application key.
        :param app_key: The secret value of the application key to be used for authentication.
        :returns: A dict with the json-encoded response data.
        :raises BlazeError: If failed to make the request to the server.
        :raises ResponseError: If the server returned an error.
        """
        self.account_id = account_id or self.account_id
        self.app_key = app_key or self.app_key
        response = self._http.get(self.BASE_URL + Endpoints.auth.value,
                                  auth=HTTPBasicAuth(self.account_id, self.app_key))
        data = json_loads(response.text)
        check_b2_errors(
            data, 'Failed to authenticate with BackBlaze (account_id={}, app_key={}) ({})'.format(
                self.account_id, self.app_key, data))
        self.api_url = data['apiUrl']
        self.auth_token = data['authorizationToken']
        self.download_url = data['downloadUrl']
        allowed = data.get('allowed', {})
        self._capabilities = allowed.get('capabilities', [])
        allowed_bucket_id = allowed.get('bucketId', '')
        allowed_bucket_name = allowed.get('bucketName', '')
        if allowed_bucket_id:
            self._bucket_id = allowed_bucket_id
            self._limited_account = True
        if allowed_bucket_name:
            self._bucket_name = allowed_bucket_name
            self._limited_account = True
        if self.limited_account:
            self.set_prefix(allowed.get('namePrefix', ''))
        return data

    def create_bucket(self, bucket_name:str, private:bool, bucket_info:Optional[Json]=None,
                      cors_rules:Optional[Json]=None, lifecycle_rules:Optional[Json]=None) -> Json:
        """
        Creates a bucket to which you can upload files.
        Bucket creation is slow, thus this method can take a reasonably long time (30s+) to return.

        :param bucket_name: The name of the bucket to be created.
        :param private: True to set the bucket to private, False to leave it public. Private files
                        can be downloaded by others if an authorization token is provided.
        :param bucket_info: User-defined information to be stored with the bucket.
        :param cors_rules: The initial CORS rules for the bucket.
        :param lifecycle_rules: The initial lifecycle rules for the bucket.
        :returns: A json-like 9-dict containing the keys: accountId, bucketId, bucketName,
                  bucketType, bucketInfo, corsRules, lifecycleRules, revision, options.
        :raises RequestError: If the user is not authenticated.
        :raises RequestError: If the bucket name is not valid.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_create_bucket.html>`_.
        .. seealso:: `Buckets <https://www.backblaze.com/b2/docs/buckets.html>`_.
        .. seealso:: `CORS Rules <https://www.backblaze.com/b2/docs/cors_rules.html>`_.
        .. seealso:: `Lifecycle Rules <https://www.backblaze.com/b2/docs/lifecycle_rules.html>`_.
        """
        self._ensure_auth()
        if not valid_bucket_name(bucket_name):
            raise RequestError(f'Invalid bucket name "{bucket_name}".')
        params = self._base_params()
        params.update({
            'bucketName': bucket_name,
            'bucketType': self.BUCKET_TYPE_PRIVATE if private else self.BUCKET_TYPE_PUBLIC,
            'bucketInfo': bucket_info,
            'corsRules': cors_rules,
            'lifecycleRules': lifecycle_rules,
        })
        # Endpoint /b2_create_bucket can take a long time to respond, a larger timeout is required
        response = self._http.post(self._make_url(Endpoints.create_bucket.value), json=params,
                                   headers=self._headers(), timeout=90.0)
        data = json_loads(response.text)
        check_b2_errors(data, f'Failed to create bucket "{bucket_name}" ({data}).')
        return data

    def delete_bucket(self, bucket_id:str) -> Json:
        """
        Deletes a bucket.

        :param bucket_id: The id of the bucket to be deleted.
        :returns: A dict with the json-encoded response data.
        :raises RequestError: If the user is not authenticated.
        """
        self._ensure_auth()
        params = self._base_params()
        params.update({'bucketId': bucket_id})
        # Endpoint /b2_delete_bucket takes a long time to respond, so a larger timeout is warranted
        response = self._http.post(self._make_url(Endpoints.delete_bucket.value), json=params,
                                   headers=self._headers(), timeout=90.0)
        data = json_loads(response.text)
        check_b2_errors(data, f'Failed to delete bucket with id "{bucket_id}" ({data}).')
        return data

    def list_buckets(self, bucket_id:Optional[str]=None, bucket_name:Optional[str]=None,
                     bucket_types:Optional[str]=None) -> Json:
        """
        Lists all buckets associated with the authenticated account. This method can be used to
        get a single bucket information by passing the 'bucket_id' or 'bucket_name' parameters.

        :param bucket_id: If specified, will fetch only the bucket with that ID. If the bucket is
                          not found, the server will return an empty list.
        :param bucket_name: If specified, will fetch only the bucket with that name. If the bucket
                            is not found, the server will return an empty list.
        :param bucket_types: Used to filter private or public buckets. Valid values are
                             ('allPublic', 'allPrivate', 'snapshot', 'all').
        :returns: A dict with the json-encoded response data.
        :raises RequestError: If the user is not authenticated.
        :raises ResponseError: If the server returned an error.
        """
        self._ensure_auth()
        params = self._base_params()
        params.update({
            'bucketId': bucket_id,
            'bucketName': bucket_name,
            'bucketTypes': bucket_types,
        })
        response = self._http.post(self._make_url(Endpoints.list_buckets.value), json=params,
                                   headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, f'Failed to list buckets ({data}).')
        return data

    def get_upload_url(self, bucket_id:str) -> Json:
        """
        Gets the URL to upload to a bucket.

        :param bucket_id: The ID of the bucket to which files will be uploaded to.
        :returns: A json-like 3-dict containing the keys: bucketId, uploadUrl, authorizationToken.
        :raises ResponseError: If failed to obtain the upload information.
        """
        self._ensure_auth()
        response = self._http.post(self._make_url(Endpoints.get_upload_url.value),
                                   json={'bucketId': bucket_id}, headers=self._headers())
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to get uploading authorization: {result}.')
        self.upload_url = result['uploadUrl']
        self.upload_token = result['authorizationToken']
        self._bucket_id = bucket_id
        return result

    # pylint: disable = too-many-locals  # The request takes this many parameters
    def upload_file(self, data:bytes, upload_url:str, auth_token:str, file_name:str,
                    content_type:str='', last_modified_ms:Optional[int]=None,
                    content_disposition:Optional[str]=None, language:Optional[str]=None,
                    expires:Optional[str]=None, cache_control:Optional[str]=None,
                    encoding:Optional[str]=None, content_type_header:Optional[str]=None,
                    info:Optional[Dict[str, str]]=None) -> Json:
        self._ensure_auth()
        headers = {
            'Authorization': auth_token,
            'X-Bz-File-Name': quote(file_name),
            'Content-Type': content_type if content_type else 'b2/x-auto',
            'Content-Length': str(len(data)),
            'X-Bz-Content-Sha1': sha1(data).hexdigest(),
            'X-Bz-Info-src_last_modified_millis': last_modified_ms,
            'X-Bz-Info-b2-content-disposition': content_disposition,
            'X-Bz-Info-b2-content-language': language,
            'X-Bz-Info-b2-expires': expires,
            'X-Bz-Info-b2-cache-control': cache_control,
            'X-Bz-Info-b2-content-encoding': encoding,
            'X-Bz-Info-b2-content-type': content_type_header,
        }
        if info:
            headers.update({f'X-Bz-Info-{key}':quote(value) for key, value in info.items()})
        response = self._http.post(upload_url, data=data, headers=headers, timeout=None)
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to upload file "{file_name}": {result}')
        return result
    # pylint: enable = too-many-locals

    def start_large_file(self, bucket_id:str, file_name:str, content_type:str='b2/x-auto',
                         file_info:Optional[Json]=None) -> Json:
        """
        :returns: A json-like 11-dict containing the keys: accountId, action, bucketId, contentType,
                  contentLength, contentSha1, contentMd5, fileId, fileInfo, fileName,
                  uploadTimestamp.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_start_large_file.html>`_.
        """
        self._ensure_auth()
        params = {
            'bucketId': bucket_id,
            'fileName': quote(file_name),
            'contentType': content_type,
            'fileInfo': file_info,
        }
        response = self._http.post(self._make_url(Endpoints.start_large_file.value), json=params,
                                   headers=self._headers())
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to start large file upload: {result}')
        return result

    def get_upload_part_url(self, file_id:str) -> Json:
        """
        :returns: A json-like 3-dict containing the keys: fileId, uploadUrl, authorizationToken.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_get_upload_part_url.html>`_.
        """
        self._ensure_auth()
        response = self._http.post(self._make_url(Endpoints.get_upload_part_url.value),
                                   json={'fileId': file_id}, headers=self._headers())
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to get upload part url for file "{file_id}": {result}')
        return result

    def upload_part(self, data:bytes, upload_url:str, part_number:int, auth_token:str) -> Json:
        """
        Uploads part of a large file.

        :param data: The partial file data being uploaded.
        :param upload_url: The URL used to upload the partial file data.
        :param part_number: The number of the part. Be aware that part numbers start at 1, not 0!
        :param auth_token: The authorization token returned by BackBlazeB2.get_upload_part_url().
        :returns: A json-like 6-dict containing the keys:  fileId, partNumber, contentLength,
                  contentSha1, contentMd5, uploadTimestamp.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_upload_part.html>`_.
        """
        self._ensure_auth()
        headers = {
            'Authorization': auth_token,
            'X-Bz-Part-Number': str(part_number),
            'Content-Length': str(len(data)),
            'X-Bz-Content-Sha1': sha1(data).hexdigest(),
        }
        response = self._http.post(upload_url, data=data, headers=headers, timeout=None)
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to upload file part number #{part_number}: {result}')
        return result

    def finish_large_file(self, file_id:str, parts_sha1:List[str]) -> Json:
        """
        :param file_id: The ID returned by b2_start_large_file.
        :param parts_sha1: A list of hex SHA1 checksums of the parts of the large file.
        :returns: A json-like 11-dict containing the keys: accountId, action, bucketId, fileName,
                  fileId, contentLength, contentSha1, contentMd5, contentType, fileInfo,
                  uploadTimestamp.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_finish_large_file.html>`_.
        """
        self._ensure_auth()
        params = {
            'fileId': file_id,
            'partSha1Array': parts_sha1,
        }
        response = self._http.post(self._make_url(Endpoints.finish_large_file.value), json=params,
                                   headers=self._headers())
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to finish large file with id "{file_id}": {result}')
        return result

    def cancel_large_file(self, file_id:str) -> Json:
        """
        Cancels a large file upload and deletes the parts that were already uploaded.

        :param file_id: The file id returned by BackBlazeB2.start_large_file().
        :returns: A json-like 4-dict containing the keys: fileId, accountId, bucketId, fileName.
        .. seealso:: `Reference <https://www.backblaze.com/b2/docs/b2_cancel_large_file.html>`_.
        """
        self._ensure_auth()
        response = self._http.post(self._make_url(Endpoints.cancel_large_file.value),
                                   json={'fileId': file_id}, headers=self._headers())
        result = json_loads(response.text)
        check_b2_errors(result, f'Failed to cancel large file with id "{file_id}": {result}')
        return result

    def list_files(self, prefix:Optional[str]=None, delimiter:Optional[str]=None, max_files:int=0,
                   start_name:str='', bucket_id:Optional[str]=None) -> Json:
        """
        Lists the files contained on a bucket and show their information.
        The file information shown for each file is the same as returned by "get_file_info()".
        See `b2_list_file_names <https://www.backblaze.com/b2/docs/b2_list_file_names.html>`_.

        :param prefix: Returns only files which names start with the specified prefix.
        :param delimiter: Used to list only files in a directory.
        :param max_files: Number of files to return in the response. Maximum is 10000, default 100.
        :param start_name: If a file matches this path, it will be the first file returned.
        :param bucket_id: The id of the bucket to have its files listed. If empty, will try to use
                          the bucket set with BackBlazeB2.set_bucket().
        :returns: A dict with the json-encoded response data.
        :raises RequestError: If the user is not authenticated.

        :example:

        >>> # List all files which name starts with 'foo'
        >>> BackBlazeB2().list_files(prefix='foo')
        >>> # List all files with the in the 'snafu' virtual folder
        >>> BackBlazeB2().list_files(prefix='snafu/', delimiter='/')

        """
        self._ensure_auth()
        if not prefix or self.limited_account:
            prefix = self.prefix()
        params = {
            'bucketId': bucket_id if bucket_id else self.bucket_id,
            'prefix': prefix,
            'delimiter': delimiter if delimiter is not None else self.delimiter,
            'maxFileCount': max_files,
            'startFileName': start_name,
        }
        response = self._http.post(self._make_url(Endpoints.list_files.value), json=params,
                                   headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(
            data, 'Failed to get list files <prefix={}, delimiter={}, start_name={}, max_files={}, '
            'bucket_id={}> ({}).'.format(prefix, delimiter, start_name, max_files, bucket_id,
                                         data.get('message', '')))
        return data

    def get_file_info(self, file_id:str) -> Json:
        """
        Gets the information for a file on the server.
        The content of this response is the same as the one in each file listed by "list_files()".

        :param file_id: The ID given to the file when it was uploaded.
        :returns: A dict with the json-encoded response data.
        :raises RequestError: If the user is not authenticated.
        :raises ResponseError: If the server returned an error (e.g.: file does not exist).
        """
        self._ensure_auth()
        response = self._http.post(self._make_url(Endpoints.file_info.value),
                                   json={'fileId': quote(file_id)}, headers=self._headers())

        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to get files info  <file_id={}> ({}).'.format(
            file_id, data.get('message', '')))
        return data

    def download_url_id(self, file_id:Optional[str]=None,
                        auth_token:str='') -> Tuple[str, Dict[str, str]]:
        """
        Gets the download URL to a file, which can then be used to download the file.

        :param file_id: The id of the file, as returned by get_file_info() or similar methods.
        :param file_name: The full name of the file. Must be used in conjunction with the
                          "bucket_name" parameter.
        :param bucket_name: The name of the bucket where the file is. Must be used in conjunction
                            with the "file_name" parameter.
        :returns: The URL to the file.
        :raises RequestError: If the user is not authenticated.
        :raises RequestError: If there are insufficient parameters to create the download URL.
        """
        self._ensure_auth()
        url = '{base_url}{version}{endpoint}/?fileId={file_id}'.format(
            base_url=self.download_url, version=self.API_VERSION, file_id=file_id,
            endpoint=Endpoints.download_by_id.value)
        return (url, {'Authorization': auth_token} if auth_token else {})

    def get_download_auth(self, file_path_or_prefix:str, auth_duration:int,
                          bucket_id:str='') -> str:
        """
        Gets an authorization token for downloading specified files.

        :param file_path:
        """
        # duration = Min duration is 1 second, max is 604800 (one week).
        self._ensure_auth()
        data = {
            'bucketId': bucket_id if bucket_id else self.bucket_id,
            'fileNamePrefix': file_path_or_prefix,
            'validDurationInSeconds': auth_duration,
        }
        response = self._http.post(self._make_url(Endpoints.download_auth.value), json=data,
                                   headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to get download auth for prefix "{}" on bucket "{}": {}.'
                        .format(file_path_or_prefix, data['bucketId'], data.get('message', '')))
        return data['authorizationToken']

    def delete_file(self, file_id:str, file_path:str):
        """
        Deletes a file from the bucket.
        Both the ID and the full path of the file on the server must be provided to delete the file.

        :param file_id: The id of the file in the backblaze service.
        :param file_path: The absolute path to the file in the backblaze service.
        """
        self._ensure_auth()
        data = {'fileName': file_path, 'fileId': file_id}
        response = self._http.post(self._make_url(Endpoints.delete_file.value), json=data,
                                   headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to delete file with id "{}" and path "{}" ({}).'.format(
            file_id, file_path, data.get('message', '')))
        return data

    def create_key(self, account_id:str, capabilities:List[KeyCapabilities], key_name:str,
                   bucket_id:str='', prefix:str='', duration:int=0) -> Json:
        self._ensure_auth()
        params = {
            'accountId': account_id,
            'capabilities': [item.value for item in capabilities],
            'keyName': key_name,
        }
        if duration:
            params['validDurationInSeconds'] = duration
        if bucket_id:
            params['bucketId'] = bucket_id
        if prefix:
            params['namePrefix'] = prefix
        response = self._http.post(self._make_url(Endpoints.create_key.value), json=params,
                                   headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to create key "{}": {}.'.format(key_name,
                                                                      data.get('message', '')))
        return data

    def list_keys(self, account_id:str, max_key_count:int=0, start_app_key_id:str=''):
        self._ensure_auth()
        params = {'accountId': account_id}
        if max_key_count:
            params['maxKeyCount'] = max_key_count
        if start_app_key_id:
            params['startApplicationKeyId'] = start_app_key_id
        response = self._http.post(self._make_url(Endpoints.list_keys.value),
                                   json=params, headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to list keys: {}.'.format(data.get('message', '')))
        return data

    def delete_key(self, key_id:str) -> Json:
        self._ensure_auth()
        response = self._http.post(self._make_url(Endpoints.delete_key.value),
                                   json={'applicationKeyId': key_id}, headers=self._headers())
        data = json_loads(response.text)
        check_b2_errors(data, 'Failed to delete key "{}": {}.'.format(key_id,
                                                                      data.get('message', '')))
        return data
    # endregion

    # region Shortcut methods
    def download_file(self, url:str, save_path:Union[str, Path],):
        """
        Downloads a file from the server to the file system. This is a blocking operation.
        The file can be downloaded using either its ID or by specifying bucket_name + file_name.

        :param save_path: The path where the file will be written (must include the file name).
        :param url: The URL of the file to be downloaded.
                    Use download_url_path() or download_url_id() to get the file url.
        """
        self._ensure_auth()
        dir_path = Path(save_path).parent
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as file_handle:
            response = self._http.get(url, allow_redirects=True, headers=self._headers(),
                                      timeout=None)
            file_handle.write(response.content)

    def upload_large_file(self, file_or_path:Union[BinaryIO, Path], file_name:str, file_size:int=0,
                          bucket_id:str='') -> UploadGenerator:
        """
        Uploads a large file from the file system over multiple requests.
        A large file is any file larger than the current BackBlazeB2.part_size value.

        :param file_path: The path to the file on the file system.
        :param bucket_id: The id of the bucket where to upload the file.
        :param file_name: The name to give to the file in the backblaze server.
        :returns: The file-uploading generator.
        :yields: A 3-tuple containing (upload response, part number, total part count). The part
                 number starts at 1, and if the upload is successfull, the final tuple will have
                 part number 0 and the response will contain the finalized file data.
        """
        self._ensure_auth()
        is_path = isinstance(file_or_path, (str, Path))
        if is_path:
            path_or_size = file_or_path
        elif not file_size:
            raise ValueError("You must specify the file size when uploading an opened file")
        else:
            path_or_size = file_size
        _, parts_count, parts_size = upload_parts_count(path_or_size, self.part_size)
        file_id = self.start_large_file(bucket_id if bucket_id else self.bucket_id,
                                        file_name)['fileId']
        file_handle = open(file_or_path, 'rb') if isinstance(file_or_path, (str, Path)) \
            else file_or_path
        try:
            parts_sha1 = []
            for i in range(parts_count):
                upload_url_data = self.get_upload_part_url(file_id)
                upload_result = self.upload_part(file_handle.read(parts_size),
                                                 upload_url_data['uploadUrl'], i + 1,
                                                 upload_url_data['authorizationToken'])
                parts_sha1.append(upload_result['contentSha1'])
                yield (upload_result, i + 1, parts_count)
            yield (self.finish_large_file(file_id, parts_sha1), 0, parts_count)
        except (BlazeError, RequestError) as error:
            self.cancel_large_file(file_id)
            raise error
        finally:
            if is_path:
                file_handle.close()

    def upload_path(self, file_path:Path, file_name:str='', append_filename:bool=False,
                    bucket_id:str='') -> UploadGenerator:
        """
        Uploads an arbitrarily-sized file from the file system, automatically choosing either a
        single or multi-part upload.

        :param file_path: The path to the file to be uploaded.
        :param file_name: The name to be given to the file in the backblaze server.
        :param append_filename: True to append the local file name to the server file name.
        :param bucket_id: The id of the bucket to which upload the file. If empty, will use the
                          currently-set bucket.
        :returns: The file-uploading generator.
        :yields: A 3-tuple containing (upload response, part number, total part count). The part
                 number starts at 1, and if the upload is successfull, the final tuple will have
                 part number 0 and the response will contain the finalized file data.
        """
        self._ensure_auth()
        parts_count = upload_parts_count(file_path, self.part_size)[1]
        if not file_name:
            file_name = file_path.name
        elif append_filename:
            file_name = self.append_filename(file_name, file_path.name)
        bucket_id = bucket_id if bucket_id else self.bucket_id
        if parts_count == 1:
            upload_data = self.get_upload_url(bucket_id)
            with open(file_path, 'rb') as file_handle:
                data = file_handle.read()
            return self._upload_file_gen(
                data, upload_data['uploadUrl'], upload_data['authorizationToken'], file_name)
        return self.upload_large_file(file_path, file_name, bucket_id=bucket_id)

    def upload_io(self, file:BinaryIO, file_size:int, file_name:str,
                  bucket_id:str='') -> UploadGenerator:
        """
        Uploads an arbitrarily-sized file-like object, automatically choosing either a single or
        multi-part upload given its size.

        :param file: The file to be uploaded.
        :param file_size: The total size (in bytes) of the file being uploaded.
        :param file_name: The name to be given to the file in the backblaze server.
        :param bucket_id: The id of the bucket to which upload the file. If empty, will use the
                          currently-set bucket.
        :returns: The file-uploading generator.
        :yields: A 3-tuple containing (upload response, part number, total part count). The part
                 number starts at 1, and if the upload is successfull, the final tuple will have
                 part number 0 and the response will contain the finalized file data.
        """
        self._ensure_auth()
        file.seek(0)
        parts_count = upload_parts_count(file_size, self.part_size)[1]
        bucket_id = bucket_id if bucket_id else self.bucket_id
        if parts_count == 1:
            upload_data = self.get_upload_url(bucket_id)
            return self._upload_file_gen(
                file.read(), upload_data['uploadUrl'], upload_data['authorizationToken'], file_name)
        return self.upload_large_file(file, file_name, file_size, bucket_id)

    def upload(self, file_or_path:Union[str, Path, BinaryIO], file_name:str='',
               append_filename:bool=False, file_size:int=0, bucket_id:str='') -> UploadGenerator:
        """
        Uploads a file using an opened file or the path to the file in the file system.
        This method will automatically upload using multiple parts if the file is larger than the
        configured part_size.

        :param file_or_path: The opened file or path to the file to be uploaded.
        :param file_name: The name to be given to the file in the backblaze server.
        :param append_filename: True to append the local file name to the server file name.
                                Only usable when uploading from a path.
        :param file_size: The total size (in bytes) of the file being uploaded.
                          Required when uploading from an opened file.
        :param bucket_id: The id of the bucket to which the file will be uploaded. If empty, will
                          try to use the currently-set bucket's id.
        :returns: The file-uploading generator.
        :yields: A 3-tuple containing (upload response, part number, total part count). The part
                 number starts at 1, and if the upload is successfull, the final tuple will have
                 part number 0 and the response will contain the finalized file data.
        """
        if isinstance(file_or_path, (str, Path)):
            return self.upload_path(file_or_path, file_name, append_filename, bucket_id)
        if not file_size:
            raise ValueError('File size must be specified when uploading an opened file')
        return self.upload_io(file_or_path, file_size, file_name, bucket_id)
    # endregion
