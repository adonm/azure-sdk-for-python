# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=docstring-keyword-should-match-keyword-only

from typing import (
    Any, cast, Dict, Optional, Union,
    TYPE_CHECKING
)
from typing_extensions import Self

from azure.core.async_paging import AsyncItemPaged
from azure.core.pipeline import AsyncPipeline
from azure.core.tracing.decorator import distributed_trace
from azure.core.tracing.decorator_async import distributed_trace_async
from azure.storage.blob.aio import BlobServiceClient
from .._data_lake_service_client_helpers import _format_url, _parse_url
from .._deserialize import get_datalake_service_properties
from .._generated.aio import AzureDataLakeStorageRESTAPI
from .._models import (
    DirectoryProperties,
    FileProperties,
    FileSystemProperties,
    LocationMode,
    UserDelegationKey
)
from .._serialize import convert_dfs_url_to_blob_url, get_api_version
from .._shared.base_client import parse_query, StorageAccountHostsMixin
from .._shared.base_client_async import AsyncStorageAccountHostsMixin, AsyncTransportWrapper, parse_connection_str
from .._shared.policies_async import ExponentialRetry
from ._data_lake_directory_client_async import DataLakeDirectoryClient
from ._data_lake_file_client_async import DataLakeFileClient
from ._file_system_client_async import FileSystemClient
from ._models import FileSystemPropertiesPaged

if TYPE_CHECKING:
    from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
    from azure.core.credentials_async import AsyncTokenCredential
    from datetime import datetime
    from .._models import PublicAccess


class DataLakeServiceClient(AsyncStorageAccountHostsMixin, StorageAccountHostsMixin):  # type: ignore [misc]
    """A client to interact with the DataLake Service at the account level.

    This client provides operations to retrieve and configure the account properties
    as well as list, create and delete file systems within the account.
    For operations relating to a specific file system, directory or file, clients for those entities
    can also be retrieved using the `get_client` functions.

    :param str account_url:
        The URL to the DataLake storage account. Any other entities included
        in the URL path (e.g. file system or file) will be discarded. This URL can be optionally
        authenticated with a SAS token.
    :param credential:
        The credentials with which to authenticate. This is optional if the
        account URL already has a SAS token. The value can be a SAS token string,
        an instance of a AzureSasCredential or AzureNamedKeyCredential from azure.core.credentials,
        an account shared access key, or an instance of a TokenCredentials class from azure.identity.
        If the resource URI already contains a SAS token, this will be ignored in favor of an explicit credential
        - except in the case of AzureSasCredential, where the conflicting SAS tokens will raise a ValueError.
        If using an instance of AzureNamedKeyCredential, "name" should be the storage account name, and "key"
        should be the storage account key.
    :type credential:
        ~azure.core.credentials.AzureNamedKeyCredential or
        ~azure.core.credentials.AzureSasCredential or
        ~azure.core.credentials_async.AsyncTokenCredential or
        str or Dict[str, str] or None
    :keyword str api_version:
        The Storage API version to use for requests. Default value is the most recent service version that is
        compatible with the current SDK. Setting to an older version may result in reduced feature compatibility.
    :keyword str audience: The audience to use when requesting tokens for Azure Active Directory
        authentication. Only has an effect when credential is of type AsyncTokenCredential. The value could be
        https://storage.azure.com/ (default) or https://<account>.blob.core.windows.net.

    .. admonition:: Example:

        .. literalinclude:: ../samples/datalake_samples_service_async.py
            :start-after: [START create_datalake_service_client]
            :end-before: [END create_datalake_service_client]
            :language: python
            :dedent: 4
            :caption: Creating the DataLakeServiceClient from connection string.

        .. literalinclude:: ../samples/datalake_samples_service_async.py
            :start-after: [START create_datalake_service_client_oauth]
            :end-before: [END create_datalake_service_client_oauth]
            :language: python
            :dedent: 4
            :caption: Creating the DataLakeServiceClient with Azure Identity credentials.
    """

    url: str
    """The full endpoint URL to the datalake service endpoint."""
    primary_endpoint: str
    """The full primary endpoint URL."""
    primary_hostname: str
    """The hostname of the primary endpoint."""

    def __init__(
        self, account_url: str,
        credential: Optional[Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", "AsyncTokenCredential"]] = None,  # pylint: disable=line-too-long
        **kwargs: Any
    ) -> None:
        kwargs['retry_policy'] = kwargs.get('retry_policy') or ExponentialRetry(**kwargs)

        parsed_url = _parse_url(account_url=account_url)
        blob_account_url = convert_dfs_url_to_blob_url(account_url)
        self._blob_account_url = blob_account_url

        self._blob_service_client = BlobServiceClient(self._blob_account_url, credential, **kwargs)
        self._blob_service_client._hosts[LocationMode.SECONDARY] = ""

        _, sas_token = parse_query(parsed_url.query)
        self._query_str, self._raw_credential = self._format_query_string(sas_token, credential)

        super(DataLakeServiceClient, self).__init__(parsed_url, service='dfs',
                                                    credential=self._raw_credential, **kwargs)
        # ADLS doesn't support secondary endpoint, make sure it's empty
        self._hosts[LocationMode.SECONDARY] = ""

        self._client = AzureDataLakeStorageRESTAPI(self.url, base_url=self.url, pipeline=self._pipeline)
        self._client._config.version = get_api_version(kwargs)  # type: ignore [assignment]
        self._loop = kwargs.get('loop', None)

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        await self._blob_service_client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._blob_service_client.__aexit__(*args)
        await self._client.__aexit__(*args)

    async def close(self) -> None:  # type: ignore
        """ This method is to close the sockets opened by the client.
        It need not be used when using with a context manager.

        :return: None
        :rtype: None
        """
        await self._blob_service_client.close()
        await self._client.close()

    def _format_url(self, hostname: str) -> str:
        """Format the endpoint URL according to hostname.

        :param str hostname: The hostname for the endpoint URL.
        :returns: The formatted URL
        :rtype: str
        """
        return _format_url(self.scheme, hostname, self._query_str)

    @classmethod
    def from_connection_string(
        cls, conn_str: str,
        credential: Optional[Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", "AsyncTokenCredential"]] = None,  # pylint: disable=line-too-long
        **kwargs: Any
    ) -> Self:
        """
        Create DataLakeServiceClient from a Connection String.

        :param str conn_str:
            A connection string to an Azure Storage account.
        :param credential:
            The credentials with which to authenticate. This is optional if the
            account URL already has a SAS token, or the connection string already has shared
            access key values. The value can be a SAS token string,
            an instance of a AzureSasCredential from azure.core.credentials, an account shared access
            key, or an instance of a TokenCredentials class from azure.identity.
            Credentials provided here will take precedence over those in the connection string.
        :type credential:
            ~azure.core.credentials.AzureNamedKeyCredential or
            ~azure.core.credentials.AzureSasCredential or
            ~azure.core.credentials_async.AsyncTokenCredential or
            str or Dict[str, str] or None
        :keyword str audience: The audience to use when requesting tokens for Azure Active Directory
            authentication. Only has an effect when credential is of type AsyncTokenCredential. The value could be
            https://storage.azure.com/ (default) or https://<account>.blob.core.windows.net.
        :returns: A DataLakeServiceClient.
        :rtype: ~azure.storage.filedatalake.DataLakeServiceClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_file_system_async.py
                :start-after: [START create_data_lake_service_client_from_conn_str]
                :end-before: [END create_data_lake_service_client_from_conn_str]
                :language: python
                :dedent: 8
                :caption: Creating the DataLakeServiceClient from a connection string.
        """
        account_url, _, credential = parse_connection_str(conn_str, credential, 'dfs')
        return cls(account_url, credential=credential, **kwargs)

    @distributed_trace_async
    async def get_user_delegation_key(
        self, key_start_time: "datetime",
        key_expiry_time: "datetime",
        **kwargs: Any
    ) -> UserDelegationKey:
        """
        Obtain a user delegation key for the purpose of signing SAS tokens.
        A token credential must be present on the service object for this request to succeed.

        :param ~datetime.datetime key_start_time:
            A DateTime value. Indicates when the key becomes valid.
        :param ~datetime.datetime key_expiry_time:
            A DateTime value. Indicates when the key stops being valid.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: The user delegation key.
        :rtype: ~azure.storage.filedatalake.UserDelegationKey

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START get_user_delegation_key]
                :end-before: [END get_user_delegation_key]
                :language: python
                :dedent: 8
                :caption: Get user delegation key from datalake service client.
        """
        delegation_key = await self._blob_service_client.get_user_delegation_key(
            key_start_time=key_start_time,
            key_expiry_time=key_expiry_time,
            **kwargs
        )
        return UserDelegationKey._from_generated(delegation_key)  # pylint: disable=protected-access

    @distributed_trace
    def list_file_systems(
        self, name_starts_with: Optional[str] = None,
        include_metadata: bool = False,
        **kwargs: Any
    ) -> AsyncItemPaged[FileSystemProperties]:
        """Returns a generator to list the file systems under the specified account.

        The generator will lazily follow the continuation tokens returned by
        the service and stop when all file systems have been returned.

        :param str name_starts_with:
            Filters the results to return only file systems whose names
            begin with the specified prefix.
        :param bool include_metadata:
            Specifies that file system metadata be returned in the response.
            The default value is `False`.
        :keyword int results_per_page:
            The maximum number of file system names to retrieve per API
            call. If the request does not specify the server will return up to 5,000 items per page.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :keyword bool include_deleted:
            Specifies that deleted file systems to be returned in the response. This is for file system restore enabled
            account. The default value is `False`.
            .. versionadded:: 12.3.0
        :keyword bool include_system:
            Flag specifying that system filesystems should be included.
            .. versionadded:: 12.6.0
        :returns: An iterable (auto-paging) of FileSystemProperties.
        :rtype: ~azure.core.async_paging.AsyncItemPaged[~azure.storage.filedatalake.FileSystemProperties]

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START list_file_systems]
                :end-before: [END list_file_systems]
                :language: python
                :dedent: 8
                :caption: Listing the file systems in the datalake service.
        """
        item_paged = cast(AsyncItemPaged[FileSystemProperties], self._blob_service_client.list_containers(
            name_starts_with=name_starts_with,
            include_metadata=include_metadata,
            **kwargs
        ))
        item_paged._page_iterator_class = FileSystemPropertiesPaged  # pylint: disable=protected-access
        return item_paged

    @distributed_trace_async
    async def create_file_system(
        self, file_system: Union[FileSystemProperties, str],
        metadata: Optional[Dict[str, str]] = None,
        public_access: Optional["PublicAccess"] = None,
        **kwargs: Any
    ) -> FileSystemClient:
        """Creates a new file system under the specified account.

        If the file system with the same name already exists, a ResourceExistsError will
        be raised. This method returns a client with which to interact with the newly
        created file system.

        :param str file_system:
            The name of the file system to create.
        :param metadata:
            A dict with name-value pairs to associate with the
            file system as metadata. Example: `{'Category':'test'}`
        :type metadata: Dict[str, str]
        :param public_access:
            Possible values include: file system, file.
        :type public_access: ~azure.storage.filedatalake.PublicAccess
        :keyword encryption_scope_options:
            Specifies the default encryption scope to set on the file system and use for
            all future writes.

            .. versionadded:: 12.9.0

        :paramtype encryption_scope_options: dict or ~azure.storage.filedatalake.EncryptionScopeOptions
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: FileSystemClient under the specified account.
        :rtype: ~azure.storage.filedatalake.FileSystemClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START create_file_system_from_service_client]
                :end-before: [END create_file_system_from_service_client]
                :language: python
                :dedent: 8
                :caption: Creating a file system in the datalake service.
        """
        file_system_client = self.get_file_system_client(file_system)
        await file_system_client.create_file_system(metadata=metadata, public_access=public_access, **kwargs)
        return file_system_client

    async def _rename_file_system(self, name: str, new_name: str, **kwargs: Any) -> FileSystemClient:
        """Renames a filesystem.

        Operation is successful only if the source filesystem exists.

        :param str name:
            The name of the filesystem to rename.
        :param str new_name:
            The new filesystem name the user wants to rename to.
        :keyword lease:
            Specify this to perform only if the lease ID given
            matches the active lease ID of the source filesystem.
        :paramtype lease: ~azure.storage.filedatalake.DataLakeLeaseClient or str
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: FileSystemClient with the newly specified name.
        :rtype: ~azure.storage.filedatalake.FileSystemClient
        """
        await self._blob_service_client._rename_container(name, new_name, **kwargs)   # pylint: disable=protected-access
        renamed_file_system = self.get_file_system_client(new_name)
        return renamed_file_system

    @distributed_trace_async
    async def undelete_file_system(self, name: str, deleted_version: str, **kwargs: Any) -> FileSystemClient:
        """Restores soft-deleted filesystem.

        Operation will only be successful if used within the specified number of days
        set in the delete retention policy.

        .. versionadded:: 12.3.0
            This operation was introduced in API version '2019-12-12'.

        :param str name:
            Specifies the name of the deleted filesystem to restore.
        :param str deleted_version:
            Specifies the version of the deleted filesystem to restore.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: The FileSystemClient of the restored soft-deleted filesystem.
        :rtype: ~azure.storage.filedatalake.FileSystemClient
        """
        new_name = kwargs.pop('new_name', None)
        await self._blob_service_client.undelete_container(name, deleted_version, new_name=new_name, **kwargs)
        file_system = self.get_file_system_client(new_name or name)
        return file_system

    @distributed_trace_async
    async def delete_file_system(
        self, file_system: Union[FileSystemProperties, str],
        **kwargs: Any
    ) -> FileSystemClient:
        """Marks the specified file system for deletion.

        The file system and any files contained within it are later deleted during garbage collection.
        If the file system is not found, a ResourceNotFoundError will be raised.

        :param file_system:
            The file system to delete. This can either be the name of the file system,
            or an instance of FileSystemProperties.
        :type file_system: str or ~azure.storage.filedatalake.FileSystemProperties
        :keyword lease:
            If specified, delete_file_system only succeeds if the
            file system's lease is active and matches this ID.
            Required if the file system has an active lease.
        :paramtype lease: ~azure.storage.filedatalake.aio.DataLakeLeaseClient or str
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: FileSystemClient after marking the specified file system for deletion.
        :rtype: ~azure.storage.filedatalake.aio.FileSystemClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START delete_file_system_from_service_client]
                :end-before: [END delete_file_system_from_service_client]
                :language: python
                :dedent: 8
                :caption: Deleting a file system in the datalake service.
        """
        file_system_client = self.get_file_system_client(file_system)
        await file_system_client.delete_file_system(**kwargs)
        return file_system_client

    def get_file_system_client(self, file_system: Union[FileSystemProperties, str]) -> FileSystemClient:
        """Get a client to interact with the specified file system.

        The file system need not already exist.

        :param file_system:
            The file system. This can either be the name of the file system,
            or an instance of FileSystemProperties.
        :type file_system: str or ~azure.storage.filedatalake.FileSystemProperties
        :returns: A FileSystemClient.
        :rtype: ~azure.storage.filedatalake.aio.FileSystemClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_file_system_async.py
                :start-after: [START create_file_system_client_from_service]
                :end-before: [END create_file_system_client_from_service]
                :language: python
                :dedent: 8
                :caption: Getting the file system client to interact with a specific file system.
        """
        if isinstance(file_system, FileSystemProperties):
            file_system_name = file_system.name
        else:
            file_system_name = file_system

        _pipeline = AsyncPipeline(
            transport=AsyncTransportWrapper(self._pipeline._transport),  # pylint: disable=protected-access
            policies=self._pipeline._impl_policies  # type: ignore [arg-type] # pylint: disable=protected-access
        )
        return FileSystemClient(self.url, file_system_name, credential=self._raw_credential,
                                api_version=self.api_version,
                                _configuration=self._config,
                                _pipeline=_pipeline, _hosts=self._hosts)

    def get_directory_client(
        self, file_system: Union[FileSystemProperties,str],
        directory: Union[DirectoryProperties, str]
    ) -> DataLakeDirectoryClient:
        """Get a client to interact with the specified directory.

        The directory need not already exist.

        :param file_system:
            The file system that the directory is in. This can either be the name of the file system,
            or an instance of FileSystemProperties.
        :type file_system: str or ~azure.storage.filedatalake.FileSystemProperties
        :param directory:
            The directory with which to interact. This can either be the name of the directory,
            or an instance of DirectoryProperties.
        :type directory: str or ~azure.storage.filedatalake.DirectoryProperties
        :returns: A DataLakeDirectoryClient.
        :rtype: ~azure.storage.filedatalake.aio.DataLakeDirectoryClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START get_directory_client_from_service_client]
                :end-before: [END get_directory_client_from_service_client]
                :language: python
                :dedent: 8
                :caption: Getting the directory client to interact with a specific directory.
        """
        if isinstance(file_system, FileSystemProperties):
            file_system_name = file_system.name
        else:
            file_system_name = file_system
        if isinstance(directory, DirectoryProperties):
            directory_name = directory.name
        else:
            directory_name = directory

        _pipeline = AsyncPipeline(
            transport=AsyncTransportWrapper(self._pipeline._transport),  # pylint: disable=protected-access
            policies=self._pipeline._impl_policies  # type: ignore [arg-type] # pylint: disable=protected-access
        )
        return DataLakeDirectoryClient(self.url, file_system_name, directory_name=directory_name,
                                       credential=self._raw_credential,
                                       api_version=self.api_version,
                                       _configuration=self._config, _pipeline=_pipeline,
                                       _hosts=self._hosts)

    def get_file_client(
        self, file_system: Union[FileSystemProperties, str],
        file_path: Union[FileProperties, str]
    ) -> DataLakeFileClient:
        """Get a client to interact with the specified file.

        The file need not already exist.

        :param file_system:
            The file system that the file is in. This can either be the name of the file system,
            or an instance of FileSystemProperties.
        :type file_system: str or ~azure.storage.filedatalake.FileSystemProperties
        :param file_path:
            The file with which to interact. This can either be the full path of the file(from the root directory),
            or an instance of FileProperties. eg. directory/subdirectory/file
        :type file_path: str or ~azure.storage.filedatalake.FileProperties
        :returns: A DataLakeFileClient.
        :rtype: ~azure.storage.filedatalake.aio.DataLakeFileClient

        .. admonition:: Example:

            .. literalinclude:: ../samples/datalake_samples_service_async.py
                :start-after: [START get_file_client_from_service_client]
                :end-before: [END get_file_client_from_service_client]
                :language: python
                :dedent: 8
                :caption: Getting the file client to interact with a specific file.
        """
        if isinstance(file_system, FileSystemProperties):
            file_system_name = file_system.name
        else:
            file_system_name = file_system
        if isinstance(file_path, FileProperties):
            file_path = file_path.name
        else:
            pass

        _pipeline = AsyncPipeline(
            transport=AsyncTransportWrapper(self._pipeline._transport),  # pylint: disable=protected-access
            policies=self._pipeline._impl_policies  # type: ignore [arg-type] # pylint: disable=protected-access
        )
        return DataLakeFileClient(
            self.url, file_system_name, file_path=file_path, credential=self._raw_credential,
            api_version=self.api_version,
            _hosts=self._hosts, _configuration=self._config, _pipeline=_pipeline)

    @distributed_trace_async
    async def set_service_properties(self, **kwargs: Any) -> None:
        """Sets the properties of a storage account's Datalake service, including
        Azure Storage Analytics.

        If an element (e.g. analytics_logging) is left as None, the
        existing settings on the service for that functionality are preserved.

        .. versionadded:: 12.4.0
            This operation was introduced in API version '2020-06-12'.

        :keyword analytics_logging:
            Groups the Azure Analytics Logging settings.
        :type analytics_logging: ~azure.storage.filedatalake.AnalyticsLogging
        :keyword hour_metrics:
            The hour metrics settings provide a summary of request
            statistics grouped by API in hourly aggregates.
        :type hour_metrics: ~azure.storage.filedatalake.Metrics
        :keyword minute_metrics:
            The minute metrics settings provide request statistics
            for each minute.
        :type minute_metrics: ~azure.storage.filedatalake.Metrics
        :keyword cors:
            You can include up to five CorsRule elements in the
            list. If an empty list is specified, all CORS rules will be deleted,
            and CORS will be disabled for the service.
        :type cors: list[~azure.storage.filedatalake.CorsRule]
        :keyword str target_version:
            Indicates the default version to use for requests if an incoming
            request's version is not specified.
        :keyword delete_retention_policy:
            The delete retention policy specifies whether to retain deleted files/directories.
            It also specifies the number of days and versions of file/directory to keep.
        :type delete_retention_policy: ~azure.storage.filedatalake.RetentionPolicy
        :keyword static_website:
            Specifies whether the static website feature is enabled,
            and if yes, indicates the index document and 404 error document to use.
        :type static_website: ~azure.storage.filedatalake.StaticWebsite
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        """
        await self._blob_service_client.set_service_properties(**kwargs)

    @distributed_trace_async
    async def get_service_properties(self, **kwargs: Any) -> Dict[str, Any]:
        """Gets the properties of a storage account's datalake service, including
        Azure Storage Analytics.

        .. versionadded:: 12.4.0
            This operation was introduced in API version '2020-06-12'.

        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :returns: An object containing datalake service properties such as
            analytics logging, hour/minute metrics, cors rules, etc.
        :rtype: Dict[str, Any]
        """
        props = await self._blob_service_client.get_service_properties(**kwargs)
        return get_datalake_service_properties(props)
