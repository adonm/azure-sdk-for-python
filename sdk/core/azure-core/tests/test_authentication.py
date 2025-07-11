# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE.txt in the project root for
# license information.
# -------------------------------------------------------------------------
from collections import namedtuple
import base64
import time
from itertools import product
from requests import Response
import azure.core
from azure.core.credentials import (
    AccessToken,
    AzureKeyCredential,
    AzureSasCredential,
    AzureNamedKeyCredential,
    AccessTokenInfo,
)
from azure.core.exceptions import ServiceRequestError
from azure.core.pipeline import Pipeline, PipelineRequest, PipelineContext, PipelineResponse
from azure.core.pipeline.transport import HttpTransport, HttpRequest
from azure.core.pipeline.policies import (
    BearerTokenCredentialPolicy,
    RedirectPolicy,
    SansIOHTTPPolicy,
    AzureKeyCredentialPolicy,
    AzureSasCredentialPolicy,
    SensitiveHeaderCleanupPolicy,
)
from utils import HTTP_REQUESTS

import pytest

from unittest.mock import Mock


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_adds_header(http_request):
    """The bearer token policy should add a header containing a token from its credential"""
    # 2524608000 == 01/01/2050 @ 12:00am (UTC)
    expected_token = AccessToken("expected_token", 2524608000)

    def verify_authorization_header(request):
        assert request.http_request.headers["Authorization"] == "Bearer {}".format(expected_token.token)
        return Mock()

    fake_credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=expected_token))
    policies = [BearerTokenCredentialPolicy(fake_credential, "scope"), Mock(send=verify_authorization_header)]

    pipeline = Pipeline(transport=Mock(), policies=policies)
    pipeline.run(http_request("GET", "https://spam.eggs"))

    assert fake_credential.get_token.call_count == 1

    pipeline.run(http_request("GET", "https://spam.eggs"))

    # Didn't need a new token
    assert fake_credential.get_token.call_count == 1


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_authorize_request(http_request):
    """The authorize_request method should add a header containing a token from its credential"""
    # 2524608000 == 01/01/2050 @ 12:00am (UTC)
    expected_token = AccessToken("expected_token", 2524608000)

    fake_credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=expected_token))
    policy = BearerTokenCredentialPolicy(fake_credential, "scope")
    http_req = http_request("GET", "https://spam.eggs")
    request = PipelineRequest(http_req, PipelineContext(None))

    policy.authorize_request(request, "scope", claims="foo")
    assert policy._token is expected_token
    assert http_req.headers["Authorization"] == f"Bearer {expected_token.token}"
    assert fake_credential.get_token.call_count == 1
    assert fake_credential.get_token.call_args[0] == ("scope",)
    assert fake_credential.get_token.call_args[1] == {"claims": "foo"}


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_adds_header_access_token_info(http_request):
    """The bearer token policy should also add an auth header when an AccessTokenInfo is returned."""
    # 2524608000 == 01/01/2050 @ 12:00am (UTC)
    access_token = AccessToken("other_token", 2524608000)
    expected_token = AccessTokenInfo("expected_token", 2524608000, refresh_on=2524608000)

    def verify_authorization_header(request):
        assert request.http_request.headers["Authorization"] == "Bearer {}".format(expected_token.token)
        return Mock()

    fake_credential = Mock(get_token=Mock(return_value=access_token), get_token_info=Mock(return_value=expected_token))
    policies = [BearerTokenCredentialPolicy(fake_credential, "scope"), Mock(send=verify_authorization_header)]

    pipeline = Pipeline(transport=Mock(), policies=policies)
    pipeline.run(http_request("GET", "https://spam.eggs"))

    assert fake_credential.get_token_info.call_count == 1

    pipeline.run(http_request("GET", "https://spam.eggs"))

    # Didn't need a new token
    assert fake_credential.get_token_info.call_count == 1

    # get_token should not have been called
    assert fake_credential.get_token.call_count == 0


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_authorize_request_access_token_info(http_request):
    """The authorize_request method should add a header containing a token from its credential"""
    # 2524608000 == 01/01/2050 @ 12:00am (UTC)
    expected_token = AccessTokenInfo("expected_token", 2524608000)
    fake_credential = Mock(get_token=Mock(), get_token_info=Mock(return_value=expected_token))
    policy = BearerTokenCredentialPolicy(fake_credential, "scope")
    http_req = http_request("GET", "https://spam.eggs")
    request = PipelineRequest(http_req, PipelineContext(None))

    policy.authorize_request(request, "scope", claims="foo")
    assert policy._token is expected_token
    assert http_req.headers["Authorization"] == f"Bearer {expected_token.token}"
    assert fake_credential.get_token_info.call_args[0] == ("scope",)
    assert fake_credential.get_token_info.call_args[1] == {"options": {"claims": "foo"}}


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_send(http_request):
    """The bearer token policy should invoke the next policy's send method and return the result"""
    expected_request = http_request("GET", "https://spam.eggs")
    expected_response = Mock()

    def verify_request(request):
        assert request.http_request is expected_request
        return expected_response

    def get_token(*_, **__):
        return AccessToken("***", 42)

    fake_credential = Mock(spec_set=["get_token"], get_token=get_token)
    policies = [BearerTokenCredentialPolicy(fake_credential, "scope"), Mock(send=verify_request)]
    response = Pipeline(transport=Mock(), policies=policies).run(expected_request)

    assert response is expected_response


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_token_caching(http_request):
    good_for_one_hour = AccessToken("token", int(time.time() + 3600))
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=good_for_one_hour))
    pipeline = Pipeline(transport=Mock(), policies=[BearerTokenCredentialPolicy(credential, "scope")])

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token.call_count == 1  # policy has no token at first request -> it should call get_token

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token.call_count == 1  # token is good for an hour -> policy should return it from cache

    expired_token = AccessToken("token", int(time.time()))
    credential.get_token.reset_mock()
    credential.get_token.return_value = expired_token
    pipeline = Pipeline(transport=Mock(), policies=[BearerTokenCredentialPolicy(credential, "scope")])

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token.call_count == 1

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token.call_count == 2


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_access_token_info_caching(http_request):
    """The policy should cache AccessTokenInfo instances and refresh them when necessary."""

    good_for_one_hour = AccessTokenInfo("token", int(time.time() + 3600))
    credential = Mock(get_token=Mock(return_value=Mock()), get_token_info=Mock(return_value=good_for_one_hour))
    pipeline = Pipeline(transport=Mock(), policies=[BearerTokenCredentialPolicy(credential, "scope")])

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert (
        credential.get_token_info.call_count == 1
    )  # policy has no token at first request -> it should call get_token_info

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token_info.call_count == 1  # token is good for an hour -> policy should return it from cache

    expired_token = AccessTokenInfo("token", int(time.time()))
    credential.get_token_info.reset_mock()
    credential.get_token_info.return_value = expired_token
    pipeline = Pipeline(transport=Mock(), policies=[BearerTokenCredentialPolicy(credential, "scope")])

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token_info.call_count == 1

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token_info.call_count == 2  # token is expired -> policy should call get_token_info again

    refreshable_token = AccessTokenInfo("token", int(time.time() + 3600), refresh_on=int(time.time() - 1))
    credential.get_token_info.reset_mock()
    credential.get_token_info.return_value = refreshable_token
    pipeline = Pipeline(transport=Mock(), policies=[BearerTokenCredentialPolicy(credential, "scope")])

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token_info.call_count == 1

    pipeline.run(http_request("GET", "https://spam.eggs"))
    assert credential.get_token_info.call_count == 2  # token refresh-on time has passed, call again


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_optionally_enforces_https(http_request):
    """HTTPS enforcement should be controlled by a keyword argument, and enabled by default"""

    def assert_option_popped(request, **kwargs):
        assert "enforce_https" not in kwargs, "BearerTokenCredentialPolicy didn't pop the 'enforce_https' option"
        return Mock()

    def get_token(*_, **__):
        return AccessToken("***", 42)

    credential = Mock(spec_set=["get_token"], get_token=get_token)
    pipeline = Pipeline(
        transport=Mock(send=assert_option_popped), policies=[BearerTokenCredentialPolicy(credential, "scope")]
    )

    # by default and when enforce_https=True, the policy should raise when given an insecure request
    with pytest.raises(ServiceRequestError):
        pipeline.run(http_request("GET", "http://not.secure"))
    with pytest.raises(ServiceRequestError):
        pipeline.run(http_request("GET", "http://not.secure"), enforce_https=True)

    # when enforce_https=False, an insecure request should pass
    pipeline.run(http_request("GET", "http://not.secure"), enforce_https=False)

    # https requests should always pass
    pipeline.run(http_request("GET", "https://secure"), enforce_https=False)
    pipeline.run(http_request("GET", "https://secure"), enforce_https=True)
    pipeline.run(http_request("GET", "https://secure"))


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_preserves_enforce_https_opt_out(http_request):
    """The policy should use request context to preserve an opt out from https enforcement"""

    class ContextValidator(SansIOHTTPPolicy):
        def on_request(self, request):
            assert "enforce_https" in request.context, "'enforce_https' is not in the request's context"
            return Mock()

    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=AccessToken("***", 42)))
    policies = [BearerTokenCredentialPolicy(credential, "scope"), ContextValidator()]
    pipeline = Pipeline(transport=Mock(), policies=policies)

    pipeline.run(http_request("GET", "http://not.secure"), enforce_https=False)


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_default_context(http_request):
    """The policy should call get_token with the scopes given at construction, and no keyword arguments, by default"""
    expected_scope = "scope"
    token = AccessToken("", 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    policy = BearerTokenCredentialPolicy(credential, expected_scope)
    pipeline = Pipeline(transport=Mock(), policies=[policy])

    pipeline.run(http_request("GET", "https://localhost"))

    credential.get_token.assert_called_once_with(expected_scope)


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_enable_cae(http_request):
    """The policy should set enable_cae to True in the get_token request if it is set in constructor."""
    expected_scope = "scope"
    token = AccessToken("", 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    policy = BearerTokenCredentialPolicy(credential, expected_scope, enable_cae=True)
    pipeline = Pipeline(transport=Mock(), policies=[policy])

    pipeline.run(http_request("GET", "https://localhost"))

    credential.get_token.assert_called_once_with(expected_scope, enable_cae=True)


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_context_unmodified_by_default(http_request):
    """When no options for the policy accompany a request, the policy shouldn't add anything to the request context"""

    class ContextValidator(SansIOHTTPPolicy):
        def on_request(self, request):
            assert not any(request.context), "the policy shouldn't add to the request's context"

    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=AccessToken("***", 42)))
    policies = [BearerTokenCredentialPolicy(credential, "scope"), ContextValidator()]
    pipeline = Pipeline(transport=Mock(), policies=policies)

    pipeline.run(http_request("GET", "https://secure"))


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_calls_on_challenge(http_request):
    """BearerTokenCredentialPolicy should call its on_challenge method when it receives an authentication challenge"""

    class TestPolicy(BearerTokenCredentialPolicy):
        called = False

        def on_challenge(self, request, challenge):
            self.__class__.called = True
            return False

    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=AccessToken("***", int(time.time()) + 3600)))
    policies = [TestPolicy(credential, "scope")]
    response = Mock(status_code=401, headers={"WWW-Authenticate": 'Basic realm="localhost"'})
    transport = Mock(send=Mock(return_value=response))

    pipeline = Pipeline(transport=transport, policies=policies)
    pipeline.run(http_request("GET", "https://localhost"))

    assert TestPolicy.called


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_cannot_complete_challenge(http_request):
    """BearerTokenCredentialPolicy should return the 401 response when it can't complete its challenge"""

    expected_scope = "scope"
    expected_token = AccessToken("***", int(time.time()) + 3600)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=expected_token))
    expected_response = Mock(status_code=401, headers={"WWW-Authenticate": 'Basic realm="localhost"'})
    transport = Mock(send=Mock(return_value=expected_response))
    policies = [BearerTokenCredentialPolicy(credential, expected_scope)]

    pipeline = Pipeline(transport=transport, policies=policies)
    response = pipeline.run(http_request("GET", "https://localhost"))

    assert response.http_response is expected_response
    assert transport.send.call_count == 1
    credential.get_token.assert_called_once_with(expected_scope)


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_calls_sansio_methods(http_request):
    """BearerTokenCredentialPolicy should call SansIOHttpPolicy methods as does _SansIOHTTPPolicyRunner"""

    class TestPolicy(BearerTokenCredentialPolicy):
        def __init__(self, *args, **kwargs):
            super(TestPolicy, self).__init__(*args, **kwargs)
            self.on_exception = Mock(return_value=False)
            self.on_request = Mock()
            self.on_response = Mock()

        def send(self, request):
            self.request = request
            self.response = super(TestPolicy, self).send(request)
            return self.response

    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=AccessToken("***", int(time.time()) + 3600)))
    policy = TestPolicy(credential, "scope")
    transport = Mock(send=Mock(return_value=Mock(status_code=200)))

    pipeline = Pipeline(transport=transport, policies=[policy])
    pipeline.run(http_request("GET", "https://localhost"))

    policy.on_request.assert_called_once_with(policy.request)
    policy.on_response.assert_called_once_with(policy.request, policy.response)

    # the policy should call on_exception when next.send() raises
    class TestException(Exception):
        pass

    # during the first send...
    transport = Mock(send=Mock(side_effect=TestException))
    policy = TestPolicy(credential, "scope")
    pipeline = Pipeline(transport=transport, policies=[policy])
    with pytest.raises(TestException):
        pipeline.run(http_request("GET", "https://localhost"))
    policy.on_exception.assert_called_once_with(policy.request)

    # ...or the second
    def raise_the_second_time(*args, **kwargs):
        if raise_the_second_time.calls == 0:
            raise_the_second_time.calls = 1
            return Mock(status_code=401, headers={"WWW-Authenticate": 'Basic realm="localhost"'})
        raise TestException()

    raise_the_second_time.calls = 0

    policy = TestPolicy(credential, "scope")
    policy.on_challenge = Mock(return_value=True)
    transport = Mock(send=Mock(wraps=raise_the_second_time))
    pipeline = Pipeline(transport=transport, policies=[policy])
    with pytest.raises(TestException):
        pipeline.run(http_request("GET", "https://localhost"))
    assert transport.send.call_count == 2
    policy.on_challenge.assert_called_once()
    policy.on_exception.assert_called_once_with(policy.request)


@pytest.mark.skipif(azure.core.__version__ >= "2", reason="this test applies only to azure-core 1.x")
@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_key_vault_regression(http_request):
    """Test for regression affecting azure-keyvault-* 4.0.0. This test must pass, unmodified, for all 1.x versions."""

    from azure.core.pipeline.policies._authentication import _BearerTokenCredentialPolicyBase

    credential = Mock()
    policy = _BearerTokenCredentialPolicyBase(credential)
    assert policy._credential is credential

    headers = {}
    token = "alphanums"  # cspell:disable-line
    policy._update_headers(headers, token)
    assert headers["Authorization"] == "Bearer " + token

    assert policy._need_new_token
    policy._token = AccessToken(token, time.time() + 3600)
    assert not policy._need_new_token
    assert policy._token.token == token


def test_need_new_token():
    expected_scope = "scope"
    now = int(time.time())

    policy = BearerTokenCredentialPolicy(Mock(), expected_scope)

    # Token is expired.
    policy._token = AccessToken("", now - 1200)
    assert policy._need_new_token

    # Token is about to expire within 300 seconds.
    policy._token = AccessToken("", now + 299)
    assert policy._need_new_token

    # Token still has more than 300 seconds to live.
    policy._token = AccessToken("", now + 305)
    assert not policy._need_new_token

    # Token has both expires_on and refresh_on set well into the future.
    policy._token = AccessTokenInfo("", now + 1200, refresh_on=now + 1200)
    assert not policy._need_new_token

    # Token is not close to expiring, but refresh_on is in the past.
    policy._token = AccessTokenInfo("", now + 1200, refresh_on=now - 1)
    assert policy._need_new_token

    policy._token = None
    assert policy._need_new_token


def test_need_new_token_with_external_defined_token_class():
    """Test the case where some custom credential get_token call returns a custom token object."""
    FooAccessToken = namedtuple("FooAccessToken", ["token", "expires_on"])

    expected_scope = "scope"
    now = int(time.time())

    policy = BearerTokenCredentialPolicy(Mock(), expected_scope)

    # Token is expired.
    policy._token = FooAccessToken("", now - 1200)
    assert policy._need_new_token

    # Token is about to expire within 300 seconds.
    policy._token = FooAccessToken("", now + 299)
    assert policy._need_new_token


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_azure_key_credential_policy(http_request):
    """Tests to see if we can create an AzureKeyCredentialPolicy"""

    key_header = "api_key"
    api_key = "test_key"

    def verify_authorization_header(request):
        assert request.headers[key_header] == api_key

    transport = Mock(send=verify_authorization_header)
    credential = AzureKeyCredential(api_key)
    credential_policy = AzureKeyCredentialPolicy(credential=credential, name=key_header)
    pipeline = Pipeline(transport=transport, policies=[credential_policy])

    pipeline.run(http_request("GET", "https://test_key_credential"))


def test_azure_key_credential_policy_raises():
    """Tests AzureKeyCredential and AzureKeyCredentialPolicy raises with non-compliant input parameters."""
    api_key = 1234
    key_header = 5678
    with pytest.raises(TypeError):
        credential = AzureKeyCredential(api_key)

    credential = AzureKeyCredential(str(api_key))
    with pytest.raises(TypeError):
        credential_policy = AzureKeyCredentialPolicy(credential=credential, name=key_header)

    with pytest.raises(TypeError):
        credential_policy = AzureKeyCredentialPolicy(credential=str(api_key), name=key_header)


def test_azure_key_credential_updates():
    """Tests AzureKeyCredential updates"""
    api_key = "original"

    credential = AzureKeyCredential(api_key)
    assert credential.key == api_key

    api_key = "new"
    credential.update(api_key)
    assert credential.key == api_key


combinations = [
    ("sig=test_signature", "https://test_sas_credential", "https://test_sas_credential?sig=test_signature"),
    ("?sig=test_signature", "https://test_sas_credential", "https://test_sas_credential?sig=test_signature"),
    (
        "sig=test_signature",
        "https://test_sas_credential?sig=test_signature",
        "https://test_sas_credential?sig=test_signature",
    ),
    (
        "?sig=test_signature",
        "https://test_sas_credential?sig=test_signature",
        "https://test_sas_credential?sig=test_signature",
    ),
    ("sig=test_signature", "https://test_sas_credential?", "https://test_sas_credential?sig=test_signature"),
    ("?sig=test_signature", "https://test_sas_credential?", "https://test_sas_credential?sig=test_signature"),
    (
        "sig=test_signature",
        "https://test_sas_credential?foo=bar",
        "https://test_sas_credential?foo=bar&sig=test_signature",
    ),
    (
        "?sig=test_signature",
        "https://test_sas_credential?foo=bar",
        "https://test_sas_credential?foo=bar&sig=test_signature",
    ),
]


@pytest.mark.parametrize("combinations,http_request", product(combinations, HTTP_REQUESTS))
def test_azure_sas_credential_policy(combinations, http_request):
    """Tests to see if we can create an AzureSasCredentialPolicy"""
    sas, url, expected_url = combinations

    def verify_authorization(request):
        assert request.url == expected_url

    transport = Mock(send=verify_authorization)
    credential = AzureSasCredential(sas)
    credential_policy = AzureSasCredentialPolicy(credential=credential)
    pipeline = Pipeline(transport=transport, policies=[credential_policy])

    pipeline.run(http_request("GET", url))


def test_azure_sas_credential_updates():
    """Tests AzureSasCredential updates"""
    sas = "original"

    credential = AzureSasCredential(sas)
    assert credential.signature == sas

    sas = "new"
    credential.update(sas)
    assert credential.signature == sas


def test_azure_sas_credential_policy_raises():
    """Tests AzureSasCredential and AzureSasCredentialPolicy raises with non-string input parameters."""
    sas = 1234
    with pytest.raises(TypeError):
        credential = AzureSasCredential(sas)


def test_azure_named_key_credential():
    cred = AzureNamedKeyCredential("sample_name", "samplekey")

    assert cred.named_key.name == "sample_name"
    assert cred.named_key.key == "samplekey"
    assert isinstance(cred.named_key, tuple)

    cred.update("newname", "newkey")
    assert cred.named_key.name == "newname"
    assert cred.named_key.key == "newkey"
    assert isinstance(cred.named_key, tuple)


def test_azure_named_key_credential_raises():
    with pytest.raises(TypeError, match="Both name and key must be strings."):
        cred = AzureNamedKeyCredential("sample_name", 123345)

    cred = AzureNamedKeyCredential("sample_name", "samplekey")
    assert cred.named_key.name == "sample_name"
    assert cred.named_key.key == "samplekey"

    with pytest.raises(TypeError, match="Both name and key must be strings."):
        cred.update(1234, "newkey")


def test_bearer_policy_redirect_same_domain():
    class MockTransport(HttpTransport):
        def __init__(self):
            self._first = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def close(self):
            pass

        def open(self):
            pass

        def send(self, request, **kwargs):  # type: (PipelineRequest, Any) -> PipelineResponse
            if self._first:
                self._first = False
                assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
                response = Response()
                response.status_code = 301
                response.headers["location"] = "https://localhost"
                return response
            assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
            response = Response()
            response.status_code = 200
            return response

    auth_headder = "token"
    expected_scope = "scope"
    token = AccessToken(auth_headder, 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    auth_policy = BearerTokenCredentialPolicy(credential, expected_scope)
    redirect_policy = RedirectPolicy()
    header_clean_up_policy = SensitiveHeaderCleanupPolicy()
    pipeline = Pipeline(transport=MockTransport(), policies=[redirect_policy, auth_policy, header_clean_up_policy])

    pipeline.run(HttpRequest("GET", "https://localhost"))


def test_bearer_policy_redirect_different_domain():
    class MockTransport(HttpTransport):
        def __init__(self):
            self._first = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def close(self):
            pass

        def open(self):
            pass

        def send(self, request, **kwargs):  # type: (PipelineRequest, Any) -> PipelineResponse
            if self._first:
                self._first = False
                assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
                response = Response()
                response.status_code = 301
                response.headers["location"] = "https://localhost1"
                return response
            assert not request.headers.get("Authorization")
            response = Response()
            response.status_code = 200
            return response

    auth_headder = "token"
    expected_scope = "scope"
    token = AccessToken(auth_headder, 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    auth_policy = BearerTokenCredentialPolicy(credential, expected_scope)
    redirect_policy = RedirectPolicy()
    header_clean_up_policy = SensitiveHeaderCleanupPolicy()
    pipeline = Pipeline(transport=MockTransport(), policies=[redirect_policy, auth_policy, header_clean_up_policy])

    pipeline.run(HttpRequest("GET", "https://localhost"))


def test_bearer_policy_redirect_opt_out_clean_up():
    class MockTransport(HttpTransport):
        def __init__(self):
            self._first = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def close(self):
            pass

        def open(self):
            pass

        def send(self, request, **kwargs):  # type: (PipelineRequest, Any) -> PipelineResponse
            if self._first:
                self._first = False
                assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
                response = Response()
                response.status_code = 301
                response.headers["location"] = "https://localhost1"
                return response
            assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
            response = Response()
            response.status_code = 200
            return response

    auth_headder = "token"
    expected_scope = "scope"
    token = AccessToken(auth_headder, 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    auth_policy = BearerTokenCredentialPolicy(credential, expected_scope)
    redirect_policy = RedirectPolicy()
    header_clean_up_policy = SensitiveHeaderCleanupPolicy(disable_redirect_cleanup=True)
    pipeline = Pipeline(transport=MockTransport(), policies=[redirect_policy, auth_policy, header_clean_up_policy])

    pipeline.run(HttpRequest("GET", "https://localhost"))


def test_bearer_policy_redirect_customize_sensitive_headers():
    class MockTransport(HttpTransport):
        def __init__(self):
            self._first = True

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def close(self):
            pass

        def open(self):
            pass

        def send(self, request, **kwargs):  # type: (PipelineRequest, Any) -> PipelineResponse
            if self._first:
                self._first = False
                assert request.headers["Authorization"] == "Bearer {}".format(auth_headder)
                response = Response()
                response.status_code = 301
                response.headers["location"] = "https://localhost1"
                return response
            assert request.headers.get("Authorization")
            response = Response()
            response.status_code = 200
            return response

    auth_headder = "token"
    expected_scope = "scope"
    token = AccessToken(auth_headder, 0)
    credential = Mock(spec_set=["get_token"], get_token=Mock(return_value=token))
    auth_policy = BearerTokenCredentialPolicy(credential, expected_scope)
    redirect_policy = RedirectPolicy()
    header_clean_up_policy = SensitiveHeaderCleanupPolicy(blocked_redirect_headers=["x-ms-authorization-auxiliary"])
    pipeline = Pipeline(transport=MockTransport(), policies=[redirect_policy, auth_policy, header_clean_up_policy])

    pipeline.run(HttpRequest("GET", "https://localhost"))


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_azure_http_credential_policy(http_request):
    """Tests to see if we can create an AzureHttpKeyCredentialPolicy"""

    prefix = "SharedAccessKey"
    api_key = "test_key"
    header_content = f"{prefix} {api_key}"

    def verify_authorization_header(request):
        assert request.headers["Authorization"] == header_content

    transport = Mock(send=verify_authorization_header)
    credential = AzureKeyCredential(api_key)
    credential_policy = AzureKeyCredentialPolicy(credential=credential, name="Authorization", prefix=prefix)
    pipeline = Pipeline(transport=transport, policies=[credential_policy])

    pipeline.run(http_request("GET", "https://test_key_credential"))


def test_access_token_unpack():
    """Test unpacking of AccessToken."""
    token = AccessToken("token", 42)
    assert token.token == "token"
    assert token.expires_on == 42

    token, expires_on = AccessToken("token", 42)
    assert token == "token"
    assert expires_on == 42

    with pytest.raises(ValueError):
        token, expires_on, _ = AccessToken("token", 42)


def test_access_token_subscriptable():
    """Test AccessToken property access using index values."""
    token = AccessToken("token", 42)
    assert len(token) == 2
    assert token[0] == "token"
    assert token[1] == 42


@pytest.mark.parametrize("http_request", HTTP_REQUESTS)
def test_bearer_policy_on_challenge_caches_token_with_claims(http_request):
    """Test that on_challenge caches the token when handling claims challenges"""
    # Setup credentials that return different tokens for different calls
    initial_token = AccessToken("initial_token", int(time.time()) + 3600)
    claims_token = AccessToken("claims_token", int(time.time()) + 3600)

    call_count = 0

    def mock_get_token_info(*scopes, options):
        nonlocal call_count
        call_count += 1
        if options and "claims" in options:
            return claims_token
        return initial_token

    fake_credential = Mock(spec_set=["get_token_info"], get_token_info=mock_get_token_info)
    policy = BearerTokenCredentialPolicy(fake_credential, "scope")

    # Create request and initial response
    http_req = http_request("GET", "https://example.com")
    request = PipelineRequest(
        http_req, PipelineContext(None)
    )  # Create a 401 response with insufficient_claims challenge
    test_claims = '{"access_token":{"foo":"bar"}}'
    encoded_claims = base64.urlsafe_b64encode(test_claims.encode()).decode().rstrip("=")
    challenge_header = f'Bearer error="insufficient_claims", claims="{encoded_claims}"'

    response_mock = Mock(status_code=401, headers={"WWW-Authenticate": challenge_header})
    response = PipelineResponse(request, response_mock, PipelineContext(None))

    # Call on_challenge
    result = policy.on_challenge(request, response)

    # Verify the challenge was handled successfully
    assert result is True

    # Verify the token was cached
    assert policy._token is claims_token
    assert policy._token.token == "claims_token"

    # Verify the Authorization header was set correctly
    assert request.http_request.headers["Authorization"] == "Bearer claims_token"
