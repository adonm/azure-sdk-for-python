# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from azure.identity import DefaultAzureCredential

from azure.mgmt.monitor import MonitorManagementClient

"""
# PREREQUISITES
    pip install azure-identity
    pip install azure-mgmt-monitor
# USAGE
    python create_or_update_scheduled_query_ruleswith_cross_resource.py

    Before run the sample, please set the values of the client ID, tenant ID and client secret
    of the AAD application as environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID,
    AZURE_CLIENT_SECRET. For more info about how to get the value, please see:
    https://docs.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal
"""


def main():
    client = MonitorManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id="b67f7fec-69fc-4974-9099-a26bd6ffeda3",
    )

    response = client.scheduled_query_rules.create_or_update(
        resource_group_name="Rac46PostSwapRG",
        rule_name="SampleCrossResourceAlert",
        parameters={
            "location": "eastus",
            "properties": {
                "action": {
                    "aznsAction": {
                        "actionGroup": [
                            "/subscriptions/b67f7fec-69fc-4974-9099-a26bd6ffeda3/resourceGroups/Rac46PostSwapRG/providers/microsoft.insights/actiongroups/test-ag"
                        ],
                        "emailSubject": "Cross Resource Mail!!",
                    },
                    "odata.type": "Microsoft.WindowsAzure.Management.Monitoring.Alerts.Models.Microsoft.AppInsights.Nexus.DataContracts.Resources.ScheduledQueryRules.AlertingAction",
                    "severity": "3",
                    "trigger": {"threshold": 5000, "thresholdOperator": "GreaterThan"},
                },
                "description": "Sample Cross Resource alert",
                "enabled": "true",
                "schedule": {"frequencyInMinutes": 60, "timeWindowInMinutes": 60},
                "source": {
                    "authorizedResources": [
                        "/subscriptions/b67f7fec-69fc-4974-9099-a26bd6ffeda3/resourceGroups/Rac46PostSwapRG/providers/Microsoft.OperationalInsights/workspaces/sampleWorkspace",
                        "/subscriptions/b67f7fec-69fc-4974-9099-a26bd6ffeda3/resourceGroups/Rac46PostSwapRG/providers/microsoft.insights/components/sampleAI",
                    ],
                    "dataSourceId": "/subscriptions/b67f7fec-69fc-4974-9099-a26bd6ffeda3/resourceGroups/Rac46PostSwapRG/providers/microsoft.insights/components/sampleAI",
                    "query": 'union requests, workspace("sampleWorkspace").Update',
                    "queryType": "ResultCount",
                },
            },
            "tags": {},
        },
    )
    print(response)


# x-ms-original-file: specification/monitor/resource-manager/Microsoft.Insights/stable/2018-04-16/examples/createOrUpdateScheduledQueryRuleswithCrossResource.json
if __name__ == "__main__":
    main()
