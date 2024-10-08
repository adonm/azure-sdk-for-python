# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.batch import BatchManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestBatchManagementPrivateEndpointConnectionOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(BatchManagementClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_list_by_batch_account(self, resource_group):
        response = self.client.private_endpoint_connection.list_by_batch_account(
            resource_group_name=resource_group.name,
            account_name="str",
            api_version="2024-07-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_get(self, resource_group):
        response = self.client.private_endpoint_connection.get(
            resource_group_name=resource_group.name,
            account_name="str",
            private_endpoint_connection_name="str",
            api_version="2024-07-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_begin_update(self, resource_group):
        response = self.client.private_endpoint_connection.begin_update(
            resource_group_name=resource_group.name,
            account_name="str",
            private_endpoint_connection_name="str",
            parameters={
                "etag": "str",
                "groupIds": ["str"],
                "id": "str",
                "name": "str",
                "privateEndpoint": {"id": "str"},
                "privateLinkServiceConnectionState": {"status": "str", "actionsRequired": "str", "description": "str"},
                "provisioningState": "str",
                "tags": {"str": "str"},
                "type": "str",
            },
            api_version="2024-07-01",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_begin_delete(self, resource_group):
        response = self.client.private_endpoint_connection.begin_delete(
            resource_group_name=resource_group.name,
            account_name="str",
            private_endpoint_connection_name="str",
            api_version="2024-07-01",
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...
