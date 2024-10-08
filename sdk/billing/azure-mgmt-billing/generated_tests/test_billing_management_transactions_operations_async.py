# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.billing.aio import BillingManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer
from devtools_testutils.aio import recorded_by_proxy_async

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestBillingManagementTransactionsOperationsAsync(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(BillingManagementClient, is_async=True)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_list_by_customer(self, resource_group):
        response = self.client.transactions.list_by_customer(
            billing_account_name="str",
            billing_profile_name="str",
            customer_name="str",
            period_start_date="2020-02-20",
            period_end_date="2020-02-20",
            type="str",
            api_version="2024-04-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_list_by_invoice_section(self, resource_group):
        response = self.client.transactions.list_by_invoice_section(
            billing_account_name="str",
            billing_profile_name="str",
            invoice_section_name="str",
            period_start_date="2020-02-20",
            period_end_date="2020-02-20",
            type="str",
            api_version="2024-04-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_list_by_billing_profile(self, resource_group):
        response = self.client.transactions.list_by_billing_profile(
            billing_account_name="str",
            billing_profile_name="str",
            period_start_date="2020-02-20",
            period_end_date="2020-02-20",
            type="str",
            api_version="2024-04-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_list_by_invoice(self, resource_group):
        response = self.client.transactions.list_by_invoice(
            billing_account_name="str",
            invoice_name="str",
            api_version="2024-04-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_begin_transactions_download_by_invoice(self, resource_group):
        response = await (
            await self.client.transactions.begin_transactions_download_by_invoice(
                billing_account_name="str",
                invoice_name="str",
                api_version="2024-04-01",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_get_transaction_summary_by_invoice(self, resource_group):
        response = await self.client.transactions.get_transaction_summary_by_invoice(
            billing_account_name="str",
            invoice_name="str",
            api_version="2024-04-01",
        )

        # please add some check logic here by yourself
        # ...
