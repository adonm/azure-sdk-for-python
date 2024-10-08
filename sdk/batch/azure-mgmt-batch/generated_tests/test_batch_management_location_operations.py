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
class TestBatchManagementLocationOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(BatchManagementClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_get_quotas(self, resource_group):
        response = self.client.location.get_quotas(
            location_name="str",
            api_version="2024-07-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_list_supported_virtual_machine_skus(self, resource_group):
        response = self.client.location.list_supported_virtual_machine_skus(
            location_name="str",
            api_version="2024-07-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_check_name_availability(self, resource_group):
        response = self.client.location.check_name_availability(
            location_name="str",
            parameters={"name": "str", "type": "Microsoft.Batch/batchAccounts"},
            api_version="2024-07-01",
        )

        # please add some check logic here by yourself
        # ...
