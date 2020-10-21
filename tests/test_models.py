""" Tests the blaziken.models package. """
# Meta imports
from __future__ import annotations
from typing import TYPE_CHECKING
# Built-in imports
from pathlib import Path
from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch
# Project imports
from blaziken import B2Objects
from blaziken.enums import BucketType
from blaziken.enums import FileAction
from blaziken.exceptions import BucketError
from blaziken.exceptions import FileError
from blaziken.exceptions import ResponseError
from blaziken.models import Bucket
from blaziken.models import File
from tests.utils import Responses

if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from typing import Any
    from typing import Dict


# pylint: disable = protected-access  # In tests its ok accessing private members
class B2ObjectsTests(TestCase):
    """ Tests methods and properties of the B2Objects class. """

    def setUp(self):
        """ Sets up the BackBlazeB2 mock that nearly all methods use. """
        self.patcher = patch('blaziken.models.BackBlazeB2')
        self.mock_blaze = self.patcher.start()
        self.mock_api = MagicMock()
        self.mock_blaze.return_value = self.mock_api
        self.addCleanup(self.patcher.stop)

    # region B2Objects.__init__() tests
    def test_init__api_initialized(self):
        """ The B2Objects must call the authentication method. """
        account_id ='account_id'
        app_key = 'app_key'
        B2Objects(account_id, app_key)
        self.mock_blaze.assert_called_with(account_id, app_key, False, None)
    # endregion

    # region B2Objects.properties tests
    def test_account_id(self):
        """ The account_id property must return the account id associated with the instance. """
        account_id ='account_id'
        self.mock_api.account_id = account_id
        blaze = B2Objects(account_id, '')
        self.assertEqual(blaze.account_id, account_id)

    def test_app_key(self):
        """ The app_key property must return the application key associated with the instance. """
        app_key ='app_key'
        self.mock_api.app_key = app_key
        blaze = B2Objects('', app_key)
        self.assertEqual(blaze.app_key, app_key)
    # endregion

    # region B2Objects.buckets() tests
    def test_buckets__lists_existing_buckets(self):
        """ Must return a list of Bucket instances associated with the api object. """
        self.mock_api.list_buckets.return_value = Responses.list_buckets.value.dict
        blaze = B2Objects('', '')
        buckets = blaze.buckets()
        for bucket in buckets:
            self.assertTrue(isinstance(bucket, Bucket))
            self.assertIs(bucket._api, self.mock_api)  # pylint: disable = protected-access
    # endregion

    # region B2Objects.create_bucket() tests
    def test_create_bucket__creates_a_bucket(self):
        """ Must create a bucket using the provided configuration. """
        data = Responses.create_bucket.value.dict
        self.mock_api.create_bucket.return_value = data
        blaze = B2Objects('', '')
        bucket = blaze.create_bucket(data['bucketName'], True)
        self.mock_api.create_bucket.assert_called_with(data['bucketName'], True, None, None, None)
        self.assertTrue(isinstance(bucket, Bucket))
    # endregion

    # region B2Objects.bucket() tests
    def test_bucket__valid_bucket__retrieves_bucket(self):
        """ Must retrieve a single bucket matching the specified parameters. """
        # Change response so that it only lists a single bucket
        data = Responses.list_buckets.value.dict.copy()
        del data['buckets'][1:]
        bucket_info = data['buckets'][0]
        # Mock the B2 service
        self.mock_api.list_buckets.return_value = data
        self.mock_api.limited_account = False
        blaze = B2Objects('', '')
        # Retrieve the bucket by name
        bucket = blaze.bucket(name=bucket_info['bucketName'])
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertEqual(bucket.id, bucket_info['bucketId'])
        # Retrieve the bucket by id
        bucket = blaze.bucket(bucket_id=bucket_info['bucketId'])
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertEqual(bucket.name, bucket_info['bucketName'])

    def test_bucket__get_valid_bucket_by_id__retrieves_bucket(self):
        """ Retrieving an invalid bucket results in an BucketError. """
        self.mock_api.list_buckets.return_value = {"buckets": []}
        self.mock_api.limited_account = False
        blaze = B2Objects('', '', True)
        self.assertRaises(BucketError, blaze.bucket, 'bucket that does not exist 129307yu9')
    # endregion

    # region B2Objects.create_key()
    # endregion


class BucketTests(TestCase):
    """ Tests methods and properties of the Bucket class. """

    def setUp(self):
        """ Sets up the BackBlazeB2 mock that nearly all methods use. """
        self.patcher = patch('blaziken.models.BackBlazeB2')
        self.mock_blaze = self.patcher.start()
        self.mock_api = MagicMock()
        self.mock_blaze.return_value = self.mock_api
        self.addCleanup(self.patcher.stop)

    # region Bucket.__init__() tests
    def test_init__bucket_initialized(self):
        """ Tests object attributes are being correctly initialized. """
        bucket_info = Responses.list_buckets.value.dict['buckets'][0]
        bucket = Bucket(self.mock_api, bucket_info)
        self.assertIs(bucket._api, self.mock_api)
        self.assertEqual(bucket.id, bucket_info['bucketId'])
        self.assertEqual(bucket.name, bucket_info['bucketName'])
        self.assertEqual(bucket.type, BucketType(bucket_info['bucketType']))
    # endregion

    # region Bucket.__str__() tests
    def test_str(self):
        """ Tests that the __str__ and __repr__ methods. """
        name = 'bucket_name'
        bucket_id = 'bucket_id'
        bucket = Bucket(self.mock_api, {'bucketName': name, 'bucketId': bucket_id})
        self.assertEqual(str(bucket), name)
        self.assertTrue(Bucket.__name__ in repr(bucket))
        self.assertTrue(name in repr(bucket))
        self.assertTrue(bucket_id in repr(bucket))
    # endregion

    # region Bucket.files() tests
    def test_files__lists_bucket_files(self):
        """ Tests the bucket can list its files . """
        self.mock_api.list_files.return_value = Responses.list_files.value.dict
        bucket = Bucket(self.mock_api, {'bucketId': 'bucket_id'})
        args = ('prefix', '/', 'start_name', 50)
        files = bucket.files(*args)
        self.mock_api.list_files.assert_called_with(*args, bucket.id)
        for file_ in files:
            self.assertTrue(isinstance(file_, File))
            self.assertIs(file_.bucket, bucket)
            self.assertIs(file_._api, self.mock_api)
    # endregion

    # region Bucket.more_files() tests
    def test_more_files__files_available__yields_files(self):
        """ Tests that more files are listed if available. """
        bucket = Bucket(self.mock_api, {})
        bucket.files = MagicMock()
        names = ('f1', 'f2')
        bucket.files.side_effect = [
            [File(self.mock_api, bucket, {'fileName': names[0]})],
            [File(self.mock_api, bucket, {'fileName': names[1]})],
        ]
        bucket._next_files = True
        bucket._next_params = (1, 2, 3)
        more_files_generator = bucket.more_files()
        for name in names:
            files = next(more_files_generator)
            self.assertTrue(isinstance(files, list))
            self.assertTrue(isinstance(files[0], File))
            self.assertEqual(files[0].name, name)
        self.assertRaises(RuntimeError, next, more_files_generator)

    def test_more_files__no_available_params__breaks(self):
        """ Tests that the method breaks if the paratemers for the next request are empty. """
        bucket = Bucket(self.mock_api, {})
        bucket._next_files = False
        bucket._next_params = (1, 2, 3)
        self.assertEqual([], list(bucket.more_files()))
        bucket._next_files = True
        bucket._next_params = False
        self.assertEqual([], list(bucket.more_files()))

    def test_more_files__no_more_files__breaks(self):
        """ Tests that the method breaks if the request returns empty results. """
        bucket = Bucket(self.mock_api, {})
        bucket.files = MagicMock()
        bucket.files.return_value = []
        bucket._next_files = True
        bucket._next_params = (1, 2, 3)
        self.assertEqual([], list(bucket.more_files()))
        bucket.files.assert_called_with(*bucket._next_params, bucket._next_files)
    # endregion

    # region Bucket.all_files() tests
    def test_all_files__files_available__lists_files(self):
        """ Tests that all_files calls both files() and more_files() and yields File objects. """
        bucket = Bucket(self.mock_api, {})
        names = ('f1', 'f2', 'f3',)
        f1 = File(self.mock_api, bucket, {'fileName': names[0]})
        f2 = File(self.mock_api, bucket, {'fileName': names[1]})
        f3 = File(self.mock_api, bucket, {'fileName': names[2]})
        bucket.files = MagicMock()
        bucket.more_files = MagicMock()
        bucket.files.return_value = [f1]
        bucket.more_files.return_value = [[f2], [f3]]
        args = ('prefix', 'delimiter', 0, 'start_name',)
        index = 0
        for index, bucket_file in enumerate(bucket.all_files(*args)):
            self.assertTrue(isinstance(bucket_file, File))
            self.assertIs(bucket_file._api, self.mock_api)
            self.assertEqual(bucket_file.name, names[index])
        bucket.files.assert_called_with(*args)
        bucket.more_files.assert_called()
        self.assertEqual(index, len(names) - 1)
    # endregion

    # region Bucket.folder() tests
    def test_folder__folder_with_delimiter__lists_files(self):
        """ Tests that the prefix is used as-is if it is suffixed with the delimiter. """
        bucket = Bucket(self.mock_api, {})
        bucket.files = MagicMock()
        delimiter = 'delimiter'
        prefix = 'prefix' + delimiter
        max_files = 0
        bucket.folder(prefix, delimiter, max_files)
        bucket.files.assert_called_with(prefix, delimiter, max_files)

    def test_folder__folder_without_delimiter__appends_delimiter_and_lists_files(self):
        """ Tests that the prefix is appended with the delimiter if it lacks it. """
        bucket = Bucket(self.mock_api, {})
        bucket.files = MagicMock()
        prefix = 'prefix'
        delimiter = 'delimiter'
        max_files = 0
        bucket.folder(prefix, delimiter, max_files)
        bucket.files.assert_called_with(prefix + delimiter, delimiter, max_files)
    # endregion

    # region Bucket.file() tests
    def test_file__retrieve_by_id_success__retrieves_file(self):
        """ Tests retrieving a file by its name. """
        file_info = Responses.get_file_info.value.dict
        self.mock_api.get_file_info.return_value = file_info
        bucket = Bucket(self.mock_api, {})
        file_ = bucket.file(file_id=file_info['fileId'])
        self.assertTrue(isinstance(file_, File))
        self.assertIs(file_.bucket, bucket)
        self.assertIs(file_._api, self.mock_api)
        self.assertEqual(file_.name, file_info['fileName'])

    def test_file__retrieve_by_name_success__retrieves_file(self):
        """ Tests retrieving a file by its id. """
        bucket = Bucket(self.mock_api, {})
        file_name = 'file_name'
        file_data = [File(self.mock_api, bucket, {'fileName': file_name})]
        bucket.files = MagicMock()
        bucket.files.return_value = file_data
        file_ = bucket.file(file_name=file_name)
        bucket.files.assert_called_with(start_name=file_name, max_files=1)
        self.assertTrue(isinstance(file_, File))
        self.assertIs(file_.bucket, bucket)
        self.assertIs(file_._api, self.mock_api)  # pylint: disable = protected-access
        self.assertEqual(file_.name, file_name)

    def test_file__retrieve_by_id_failure__raises_file_error(self):
        """ Tests failure when retrieving a file by its name. """
        self.mock_api.get_file_info.side_effect = ResponseError
        bucket = Bucket(self.mock_api, {})
        self.assertRaises(FileError, bucket.file, 'file_id')

    def test_file__retrieve_by_name_failure__raises_file_error(self):
        """ Tests failure when retrieving a file by its id. """
        bucket = Bucket(self.mock_api, {})
        bucket.files = MagicMock()
        bucket.files.return_value = []
        self.assertRaises(FileError, bucket.file, file_name='file_name')
    # endregion

    # region Bucket.delete() tests
    def test_delete__delete_success(self):
        """ Tests deleting the bucket. """
        bucket_id = 'bucket_id'
        bucket = Bucket(self.mock_api, {'bucketId': bucket_id})
        bucket.delete()
        self.mock_api.delete_bucket.assert_called_with(bucket.id)
    # endregion

    # region Bucket.upload() tests
    def test_upload_iter__upload_success(self):
        bucket_id = 'bucket_id'
        bucket = Bucket(self.mock_api, {'bucketId': bucket_id})
        file_info = Responses.get_file_info.json
        iter_data = [
            ({}, 1, 2),
            ({}, 2, 2),
            (file_info, 0, 2),
        ]
        self.mock_api.upload.return_value = iter(iter_data)
        args = (Path(), 'upload', True, 0)
        for iteration, expected in zip(bucket.upload_iter(*args), iter_data):
            self.assertEqual(iteration, expected)
        self.mock_api.upload.assert_called_with(*args, bucket.id)

    def test_upload__upload_success(self):
        """ Tests uploading a file to the bucket. """
        bucket_id = 'bucket_id'
        bucket = Bucket(self.mock_api, {'bucketId': bucket_id})
        file_info = Responses.get_file_info.json
        self.mock_api.upload.return_value = iter([
            ({}, 1, 2),
            ({}, 2, 2),
            (file_info, 0, 2),
        ])
        args = (Path(), 'upload', True, 0)
        file = bucket.upload(*args)
        self.assertIsInstance(file, File)
        self.assertEqual(file.api, self.mock_api)
        self.assertEqual(file.bucket, bucket)
        self.assertEqual(file.id, file_info['fileId'])
        self.assertEqual(file.name, file_info['fileName'])
        self.mock_api.upload.assert_called_with(*args, bucket.id)
    # endregion

class FileTests(TestCase):
    """ Tests methods and properties of the File class. """

    def setUp(self):
        """ Sets up the BackBlazeB2 mock that nearly all methods use. """
        self.patcher = patch('blaziken.models.BackBlazeB2')
        self.mock_blaze = self.patcher.start()
        self.mock_api = MagicMock()
        self.mock_blaze.return_value = self.mock_api
        self.addCleanup(self.patcher.stop)
        self.mock_bucket = MagicMock()

    # region File.__init__() tests
    def test_init(self):
        """ Tests object attributes are correctly initialized. """
        data = Responses.get_file_info.value.dict
        b2file = File(self.mock_api, self.mock_bucket, data)
        name_path = Path(data['fileName'])
        self.assertEqual(b2file._api, self.mock_api)
        self.assertEqual(b2file.bucket, self.mock_bucket)
        self.assertEqual(b2file.id, data['fileId'])
        self.assertEqual(b2file.name, data['fileName'])
        self.assertEqual(b2file.base_name, name_path.name)
        self.assertEqual(b2file.extension, name_path.suffix)
        self.assertEqual(b2file.size, data['contentLength'])
        self.assertEqual(b2file.action,  FileAction(data['action']))
    # endregion

    # region File.__str__() tests
    def test_str(self):
        """ Tests that the __str__ and __repr__ methods have useful info. """
        name = 'file name'
        b2file = File(None, None, {'fileName': name})
        self.assertEqual(name, str(b2file))
        self.assertIn(b2file.id, repr(b2file))
        self.assertIn(b2file.name, repr(b2file))
    # endregion

    # region File.properties tests
    def test_is_folder(self):
        """ Tests that a File is considered a folder if its action == folder or has no id. """
        self.assertTrue(File(None, None, {'action': FileAction.folder.value}).is_folder)
        self.assertTrue(File(None, None, {}).is_folder)
        self.assertFalse(File(None, None, {'fileId': 'file_id'}).is_folder)
    # endregion

    # region File.download_url() tests
    def test_download_url__public_bucket__no_auth_token_required(self):
        """ Tests that downloading from public buckets does not retrieve an auth token. """
        bucket = MagicMock()
        file_name = 'file name'
        bucket.name = 'bucket name'
        bucket.type = BucketType.public
        b2file = File(self.mock_api, bucket, {'fileName': file_name})
        b2file.download_url()
        self.mock_api.download_url_path.assert_called_with(file_name, bucket_name=bucket.name)
        self.mock_api.get_download_auth.assert_not_called()

    def test_download_url__private_bucket__auth_token_obtained(self):
        """ Tests that downloading from private buckets retrieve an auth token. """
        bucket = MagicMock()
        bucket.type = BucketType.private
        file_name = 'file name'
        bucket.id = 'bucket id'
        bucket.name = 'bucket name'
        auth_token = 'auth token'
        token_duration = 1
        self.mock_api.get_download_auth.return_value = auth_token
        b2file = File(self.mock_api, bucket, {'fileName': file_name})
        b2file.download_url(token_duration)
        self.mock_api.get_download_auth.assert_called_with(file_name, token_duration, bucket.id)
        self.mock_api.download_url_path.assert_called_with(file_name, auth_token, bucket.name)
    # endregion

    # region File.download() tests
    def test_download__path_is_file__downloads_file(self):
        """ Tests that download writes to a file. """
        path = Path(__file__)
        download_url = 'download url'
        b2file = File(self.mock_api, self.mock_bucket, {})
        b2file.download_url = MagicMock()
        b2file.download_url.return_value = download_url
        b2file.download(path)
        self.mock_api.download_file.assert_called_with(download_url, path)

    def test_download__path_is_dir__appends_filename_and_downloads_file(self):
        """ Tests that download appends a name to the path if the path points to a directory. """
        path = Path(__file__).parent
        download_url = 'download url'
        name = 'file name'
        b2file = File(self.mock_api, self.mock_bucket, {'fileName': name})
        b2file.download_url = MagicMock()
        b2file.download_url.return_value = download_url
        b2file.download(path)
        self.mock_api.download_file.assert_called_with(download_url, path / name)
    # endregion

    # region File.delete() tests
    def test_delete(self):
        """ Tests the delete method calls the delete endpoint. """
        data = Responses.get_file_info.value.dict
        b2file = File(self.mock_api, self.mock_bucket, data)
        b2file.delete()
        self.mock_api.delete_file.assert_called_with(data['fileId'], data['fileName'])
    # endregion
