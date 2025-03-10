# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
# pylint: disable=wrong-import-position

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._patch import *  # pylint: disable=unused-wildcard-import


from ._models_py3 import (  # type: ignore
    ApplicationInsightsComponent,
    ApplicationInsightsComponentListResult,
    ApplicationInsightsComponentProactiveDetectionConfiguration,
    ApplicationInsightsComponentProactiveDetectionConfigurationPropertiesRuleDefinitions,
    ComponentPurgeBody,
    ComponentPurgeBodyFilters,
    ComponentPurgeResponse,
    ComponentPurgeStatusResponse,
    ComponentsResource,
    HeaderField,
    Operation,
    OperationInfo,
    OperationsListResult,
    PrivateLinkScopedResource,
    TagsResource,
    WebTest,
    WebTestGeolocation,
    WebTestListResult,
    WebTestPropertiesConfiguration,
    WebTestPropertiesRequest,
    WebTestPropertiesValidationRules,
    WebTestPropertiesValidationRulesContentValidation,
    WebtestsResource,
)

from ._application_insights_management_client_enums import (  # type: ignore
    ApplicationType,
    FlowType,
    IngestionMode,
    PublicNetworkAccessType,
    PurgeState,
    RequestSource,
    WebTestKind,
    WebTestKindEnum,
)
from ._patch import __all__ as _patch_all
from ._patch import *
from ._patch import patch_sdk as _patch_sdk

__all__ = [
    "ApplicationInsightsComponent",
    "ApplicationInsightsComponentListResult",
    "ApplicationInsightsComponentProactiveDetectionConfiguration",
    "ApplicationInsightsComponentProactiveDetectionConfigurationPropertiesRuleDefinitions",
    "ComponentPurgeBody",
    "ComponentPurgeBodyFilters",
    "ComponentPurgeResponse",
    "ComponentPurgeStatusResponse",
    "ComponentsResource",
    "HeaderField",
    "Operation",
    "OperationInfo",
    "OperationsListResult",
    "PrivateLinkScopedResource",
    "TagsResource",
    "WebTest",
    "WebTestGeolocation",
    "WebTestListResult",
    "WebTestPropertiesConfiguration",
    "WebTestPropertiesRequest",
    "WebTestPropertiesValidationRules",
    "WebTestPropertiesValidationRulesContentValidation",
    "WebtestsResource",
    "ApplicationType",
    "FlowType",
    "IngestionMode",
    "PublicNetworkAccessType",
    "PurgeState",
    "RequestSource",
    "WebTestKind",
    "WebTestKindEnum",
]
__all__.extend([p for p in _patch_all if p not in __all__])  # pyright: ignore
_patch_sdk()
