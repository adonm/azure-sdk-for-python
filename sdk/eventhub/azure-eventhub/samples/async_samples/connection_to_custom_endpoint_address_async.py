#!/usr/bin/env python

# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

"""
Examples to show how to create async EventHubProducerClient and EventHubConsumerClient that connect to custom endpoint.
"""

import os
import asyncio
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient, EventHubConsumerClient
from azure.identity.aio import DefaultAzureCredential

FULLY_QUALIFIED_NAMESPACE = os.environ["EVENT_HUB_CONN_STR"]
EVENTHUB_NAME = os.environ["EVENT_HUB_NAME"]
# The custom endpoint address to use for establishing a connection to the Event Hubs service,
# allowing network requests to be routed through any application gateways
# or other paths needed for the host environment.
CUSTOM_ENDPOINT_ADDRESS = "sb://<custom_endpoint_hostname>:<custom_endpoint_port>"
# The optional absolute path to the custom certificate file used by client to authenticate the
# identity of the connection endpoint in the case that endpoint has its own issued CA.
# If not set, the certifi library will be used to load certificates.
CUSTOM_CA_BUNDLE_PATH = "<your_custom_ca_bundle_file_path>"


async def producer_connecting_to_custom_endpoint():
    producer_client = EventHubProducerClient(
        fully_qualified_namespace=FULLY_QUALIFIED_NAMESPACE,
        credential=DefaultAzureCredential(),
        eventhub_name=EVENTHUB_NAME,
        custom_endpoint_address=CUSTOM_ENDPOINT_ADDRESS,
        connection_verify=CUSTOM_CA_BUNDLE_PATH,
    )

    async with producer_client:
        # Without specifying partition_id or partition_key
        # the events will be distributed to available partitions via round-robin.
        event_data_batch = await producer_client.create_batch()
        event_data_batch.add(EventData("Single message"))
        await producer_client.send_batch(event_data_batch)
        print("Send a message.")


async def on_event(partition_context, event):
    # Put your code here.
    # If the operation is i/o intensive, multi-thread will have better performance.
    print("Received event from partition: {}.".format(partition_context.partition_id))


async def consumer_connecting_to_custom_endpoint():
    consumer_client = EventHubConsumerClient(
        fully_qualified_namespace=FULLY_QUALIFIED_NAMESPACE,
        credential=DefaultAzureCredential(),
        eventhub_name=EVENTHUB_NAME,
        consumer_group="$Default",
        custom_endpoint_address=CUSTOM_ENDPOINT_ADDRESS,
        connection_verify=CUSTOM_CA_BUNDLE_PATH,
    )

    try:
        async with consumer_client:
            await consumer_client.receive(
                on_event=on_event,
                starting_position="-1",  # "-1" is from the beginning of the partition.
            )
    except KeyboardInterrupt:
        print("Stopped receiving.")


asyncio.run(producer_connecting_to_custom_endpoint())
asyncio.run(consumer_connecting_to_custom_endpoint())
