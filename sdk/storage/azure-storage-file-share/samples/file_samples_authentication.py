# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: file_samples_authentication.py

DESCRIPTION:
    These samples demonstrate authenticating a client via a connection string,
    shared access key, or by generating a sas token with which the returned signature
    can be used with the credential parameter of any ShareServiceClient,
    ShareClient, ShareDirectoryClient, or ShareFileClient.

USAGE:
    python file_samples_authentication.py

    Set the environment variables with your own values before running the sample:
    1) STORAGE_CONNECTION_STRING - the connection string to your storage account
    2) STORAGE_ACCOUNT_FILE_SHARE_URL - the queue service account URL
    3) STORAGE_ACCOUNT_NAME - the name of the storage account
    4) STORAGE_ACCOUNT_KEY - the storage account access key
"""

import os
import sys
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
DEST_FILE = os.path.join(current_dir, "SampleDestination.txt")

class FileAuthSamples(object):

    connection_string = os.getenv("STORAGE_CONNECTION_STRING")

    account_url = os.getenv("STORAGE_ACCOUNT_FILE_SHARE_URL")
    account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    access_key = os.getenv("STORAGE_ACCOUNT_KEY")

    def authentication_connection_string(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: authentication_connection_string")
            sys.exit(1)

        # Instantiate the ShareServiceClient from a connection string
        # [START create_share_service_client_from_conn_string]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient.from_connection_string(self.connection_string)
        # [END create_share_service_client_from_conn_string]

    def authentication_shared_access_key(self):
        if self.account_url is None:
            print("Missing required environment variable: STORAGE_ACCOUNT_FILE_SHARE_URL." + '\n' +
                  "Test: authentication_shared_access_key")
            sys.exit(1)

        if self.access_key is None:
            print("Missing required environment variable: STORAGE_ACCOUNT_KEY." + '\n' +
                  "Test: authentication_shared_access_key")
            sys.exit(1)

        # Instantiate a ShareServiceClient using a shared access key
        # [START create_share_service_client]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient(
            account_url=self.account_url,
            credential=self.access_key
        )
        # [END create_share_service_client]

    def authentication_shared_access_signature(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: authentication_shared_access_signature")
            sys.exit(1)

        if self.account_name is None:
            print("Missing required environment variable: STORAGE_ACCOUNT_NAME." + '\n' +
                  "Test: authentication_shared_access_signature")
            sys.exit(1)

        if self.access_key is None:
            print("Missing required environment variable: STORAGE_ACCOUNT_KEY." + '\n' +
                  "Test: authentication_shared_access_signature")
            sys.exit(1)

        # Instantiate a ShareServiceClient using a connection string
        # [START generate_sas_token]
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient.from_connection_string(self.connection_string)

        # Create a SAS token to use to authenticate a new client
        from azure.storage.fileshare import generate_account_sas, ResourceTypes, AccountSasPermissions

        sas_token = generate_account_sas(
            self.account_name,
            self.access_key,
            resource_types=ResourceTypes(service=True),
            permission=AccountSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        # [END generate_sas_token]

    def authentication_default_azure_credential(self):
        if self.account_url is None:
            print("Missing required environment variable: STORAGE_ACCOUNT_FILE_SHARE_URL." + '\n' +
                  "Test: authentication_default_azure_credential")
            sys.exit(1)

        # [START file_share_oauth]
        # Get a credential for authentication
        # DefaultAzureCredential attempts a chained set of authentication methods.
        # See documentation here: https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/identity/azure-identity
        from azure.identity import DefaultAzureCredential
        default_credential = DefaultAzureCredential()

        # Instantiate a ShareServiceClient using a token credential and token_intent
        from azure.storage.fileshare import ShareServiceClient
        share_service_client = ShareServiceClient(
            account_url=self.account_url,
            credential=default_credential,
            # When using a token credential, you MUST also specify a token_intent
            token_intent='backup'
        )

        # Only Directory and File operations, and a certain few Share operations, are currently supported for OAuth.
        # Create a ShareFileClient from the ShareServiceClient.
        share_client = share_service_client.get_share_client("myshare")
        share_client.create_share()
        share_client.create_directory('mydirectory')
        directory_client = share_client.get_directory_client('mydirectory')
        with open(DEST_FILE, "wb") as data:
            directory_client.upload_file('myfile', data=data)
        share_file_client = directory_client.get_file_client('myfile')

        properties = share_file_client.get_file_properties()
        # [END file_share_oauth]


if __name__ == '__main__':
    sample = FileAuthSamples()
    sample.authentication_connection_string()
    sample.authentication_shared_access_key()
    sample.authentication_shared_access_signature()
    sample.authentication_default_azure_credential()

