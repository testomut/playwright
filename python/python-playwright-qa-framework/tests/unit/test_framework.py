import base64
import json
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError

from src.config import Settings
from src.constants.functions import format_phone_number, format_phone_number_to_formatted_number
from src.types.models import NewCustomField, RegistrationData
from src.utils import api_requests as api_module
from src.utils.api_requests import ApiError, ApiRequests, resolve_token_file_path
from src.utils.parametrization_helpers import oauth_by_role


@pytest.mark.parametrize(
    "value,display", [("2025550101", "+1 202 555 0101"), ("+1 (202) 555-0101", "+1 202 555 0101"), (None, "")]
)
def test_phone_display(value, display):
    assert format_phone_number(value) == display


def test_table_phone_format():
    assert format_phone_number_to_formatted_number("+12025550101") == "(202) 555-0101"


@pytest.mark.parametrize(
    "payload,fresh", [({"exp": 5000}, True), ({"exp": 1200}, False), ({}, False), ({"exp": "5000"}, False)]
)
def test_token_expiry(payload, fresh, monkeypatch):
    monkeypatch.setattr(api_module.time, "time", lambda: 1000)
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert ApiRequests.token_is_fresh(f"header.{encoded}.signature") is fresh


def test_invalid_token_is_not_reused():
    assert ApiRequests.token_is_fresh("invalid") is False


def test_account_token_path():
    assert resolve_token_file_path("user2.json").name == "account2.json"


def test_invalid_custom_field_is_rejected():
    with pytest.raises(ValidationError):
        NewCustomField(name="field", type="invalid", visible=True)


def test_explicit_api_base(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:9876/")
    assert Settings().api_url == "http://127.0.0.1:9876"


def test_tags_use_authenticated_request(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{"id": 1, "label": "demo"}]})

    client = ApiRequests()
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        assert client.get_tags("synthetic-token")["data"][0]["label"] == "demo"
        assert seen[0].headers["Authorization"] == "Bearer synthetic-token"
        assert seen[0].url.path == "/api/v1/public/tags"
    finally:
        client.close()


def test_api_failure_has_status():
    client = ApiRequests()
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(422)))
    try:
        with pytest.raises(ApiError, match="422"):
            client.tags("synthetic-token", "demo")
    finally:
        client.close()


def test_role_member_is_explicitly_restored():
    account = RegistrationData(
        email="owner@example.test",
        password="synthetic",
        firstName="Demo",
        lastName="Owner",
        organizationId=1,
        token="synthetic",
        member={"email": "member@example.test"},
    )
    client = Mock()
    client.get_members.return_value = [{"id": 2, "email": "member@example.test"}]
    client.login.return_value = "synthetic-member-token"
    page = Mock()
    oauth_by_role(client, account, "Member", page)
    assert client.update_user_role.call_args.args[2] == "member"
    assert page.oauth_with_token.call_count == 2
