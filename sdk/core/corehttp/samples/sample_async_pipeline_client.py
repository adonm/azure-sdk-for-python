# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: sample_pipeline_client.py

DESCRIPTION:
    This sample demonstrates how to create and use a PipelineClient.

USAGE:
    python sample_pipeline_client.py
"""
import asyncio
from typing import Iterable, Union


async def sample_pipeline_client():
    # [START build_async_pipeline_client]
    from corehttp.runtime import AsyncPipelineClient
    from corehttp.rest import HttpRequest, AsyncHttpResponse
    from corehttp.runtime.policies import (
        AsyncHTTPPolicy,
        SansIOHTTPPolicy,
        HeadersPolicy,
        UserAgentPolicy,
        AsyncRetryPolicy,
    )

    policies: Iterable[Union[AsyncHTTPPolicy, SansIOHTTPPolicy]] = [
        HeadersPolicy(),
        UserAgentPolicy("myuseragent"),
        AsyncRetryPolicy(),
    ]
    client: AsyncPipelineClient[HttpRequest, AsyncHttpResponse] = AsyncPipelineClient(
        "https://bing.com", policies=policies
    )
    request = HttpRequest("GET", "https://bing.com")
    async with client:
        response = await client.send_request(request)
        # [END build_async_pipeline_client]

        pipeline_response = await client.pipeline.run(request)
        print(response)
        print(pipeline_response)


async def main():
    await sample_pipeline_client()


if __name__ == "__main__":
    asyncio.run(main())
