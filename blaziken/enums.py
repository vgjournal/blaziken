""" Module with enums representing various options for the BackBlazeB2 service. """
from __future__ import annotations
from typing import Tuple

from enum import Enum


class Endpoints(Enum):
    """ Enum with the API endpoints urls of the backblazeb2 web service. """

    auth = '/b2_authorize_account'
    cancel_large_file = '/b2_cancel_large_file'
    create_bucket = '/b2_create_bucket'
    create_key = '/b2_create_key'
    delete_bucket = '/b2_delete_bucket'
    delete_file = '/b2_delete_file_version'
    delete_key = '/b2_delete_key'
    download_auth = '/b2_get_download_authorization'
    download_by_id ='/b2_download_file_by_id'
    file_info = '/b2_get_file_info'
    finish_large_file = '/b2_finish_large_file'
    get_upload_part_url = '/b2_get_upload_part_url'
    get_upload_url = '/b2_get_upload_url'
    list_buckets = '/b2_list_buckets'
    list_files = '/b2_list_file_names'
    list_keys = '/b2_list_keys'
    start_large_file = '/b2_start_large_file'
    upload_part ='/b2_upload_part'


class BucketType(Enum):
    """
    Enum with the available visibility types of a bucket.

    :cvar public: Anybody can download the files is the bucket.
    :cvar private: An authorization token is needed to download files from the bucket.
    :cvar snapshot: It is a private bucket containing snapshots created on the B2 web site.
    """

    public = 'allPublic'
    private = 'allPrivate'
    snapshot = 'snapshot'
    null = ''


class FileAction(Enum):
    """
    Enum with the possible states of a file in the B2 service.

    :cvar ~.upload: The "default" state, means a file has finished being uploaded to the service.
    :cvar start: A file that started upload but has not finished it or was cancelled.
    :cvar hide: Means the file is hidden and will not show when listing files of the bucket.
    :cvar folder: Means the file is a virtual folder.
    """

    upload = 'upload'
    start = 'start'
    hide = 'hide'
    folder = 'folder'
    null = ''


class KeyCapabilities(Enum):
    """ Enum with the possible values for the permissions of a key. """

    delete_buckets = 'deleteBuckets'
    delete_files = 'deleteFiles'
    delete_keys = 'deleteKeys'
    list_buckets = 'listBuckets'
    list_files = 'listFiles'
    list_keys = 'listKeys'
    read_buckets = 'readBuckets'
    read_files = 'readFiles'
    share_files = 'shareFiles'
    write_buckets = 'writeBuckets'
    write_files = 'writeFiles'
    write_keys = 'writeKeys'

    @classmethod
    def keys(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a 3-tuple of all key-related KeyCapabilities objects. """
        return (cls.write_keys, cls.list_keys, cls.delete_keys,)

    @classmethod
    def buckets(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a 3-tuple of all bucket-related KeyCapabilities objects. """
        return (cls.write_buckets, cls.read_buckets, cls.list_buckets, cls.delete_buckets,)

    @classmethod
    def files(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a 5-tuple of all file-related KeyCapabilities objects. """
        return (cls.write_files, cls.delete_files, cls.list_files, cls.read_files, cls.share_files,)

    @classmethod
    def read(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a tuple of all read KeyCapabilities objects. """
        return (cls.read_buckets, cls.read_files, cls.list_buckets, cls.list_files, cls.list_keys,)

    @classmethod
    def write(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a tuple of all write KeyCapabilities objects. """
        return (cls.write_buckets, cls.write_files, cls.write_keys,)

    @classmethod
    def delete(cls) -> Tuple[KeyCapabilities, ...]:
        """ Gets a tuple of all delete KeyCapabilities objects. """
        return (cls.delete_buckets, cls.delete_files, cls.delete_keys,)
