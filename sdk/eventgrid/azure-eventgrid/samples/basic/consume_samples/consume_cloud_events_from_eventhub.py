# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
FILE: consume_cloud_events_from_eventhub.py
DESCRIPTION:
    These samples demonstrate receiving events from an Event Hub.
USAGE:
    python consume_cloud_events_from_eventhub.py
    Set the environment variables with your own values before running the sample:
    1) EVENT_HUB_CONN_STR: The connection string to the Event hub account
    3) EVENTHUB_NAME: The name of the eventhub account
"""

# Note: This sample would not work on pypy since azure-eventhub
# depends on uamqp which is not pypy compatible.

import os
import json
from azure.core.messaging import CloudEvent
from azure.eventhub import EventHubConsumerClient
from azure.identity import DefaultAzureCredential

EVENTHUB_NAME = os.environ["EVENT_HUB_NAME"]
EVENTHUB_FULLY_QUALIFIED_NAMESPACE = os.environ["EVENT_HUB_HOSTNAME"]


def on_event(partition_context, event):
    dict_event: CloudEvent = CloudEvent.from_json(event)
    print("data: {}\n".format(dict_event.data))


consumer_client = EventHubConsumerClient(
    fully_qualified_namespace=EVENTHUB_FULLY_QUALIFIED_NAMESPACE,
    credential=DefaultAzureCredential(),
    consumer_group="$Default",
    eventhub_name=EVENTHUB_NAME,
)

with consumer_client:
    event_list = consumer_client.receive(
        on_event=on_event, starting_position="-1", prefetch=5  # "-1" is from the beginning of the partition.
    )
