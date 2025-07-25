# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import unittest
import pytest

from azure.mgmt.eventgrid import EventGridManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy


@pytest.mark.live_test_only
@pytest.mark.skip("disallowed by policy")
class TestMgmtEventGrid(AzureMgmtRecordedTestCase):

    def setup_method(self, method):
        self.eventgrid_client = self.create_mgmt_client(EventGridManagementClient)

    @pytest.mark.live_test_only
    @RandomNameResourceGroupPreparer(location="eastus2")
    @recorded_by_proxy
    def test_domain(self, resource_group, location):
        # create
        DOMAIN_NAME = self.get_resource_name("domain")
        BODY = {"location": location}
        result = self.eventgrid_client.domains.begin_create_or_update(resource_group.name, DOMAIN_NAME, BODY)
        result.result()

        # update
        BODY = {"tags": {"tag1": "value1", "tag2": "value2"}}
        result = self.eventgrid_client.domains.begin_update(resource_group.name, DOMAIN_NAME, BODY)
        result.result()

        # get
        self.eventgrid_client.domains.get(resource_group.name, DOMAIN_NAME)

        # delete
        result = self.eventgrid_client.domains.begin_delete(resource_group.name, DOMAIN_NAME)
        result.result()


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
