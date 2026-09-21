"""REST client used for seeding, cleanup and sign-in.

The rule the whole suite follows: set data up over the API, assert it in the UI. Clicking
through a wizard to create a tag a test merely needs to exist is slow and fails for reasons
that have nothing to do with what is under test.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx

from src.config import ACCOUNTS_DIR, TOKENS_DIR, settings
from src.constants.functions import format_phone_number_to_formatted_number, only_digits
from src.types.models import NewContact, NewCustomField

log = logging.getLogger(__name__)

TOKEN_EXPIRY_LEEWAY_MS = 600_000
TRANSIENT_STATUSES = (403, 429, 502, 503, 504)

JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def resolve_token_file_path(file_name: str) -> Path:
    """Map a logical token-file name to a path on disk.

    Accounts that have an account file keep their token inside it, so the file stays the single
    source of truth. Everything else gets its own file under variables/tokens/, which is ignored.

        "user0.json" -> variables/accounts/account0.json
        "old.json"   -> variables/tokens/old.json
    """
    worker = re.fullmatch(r"user(\d+)\.json", file_name)
    if worker:
        return ACCOUNTS_DIR / f"account{worker.group(1)}.json"
    return TOKENS_DIR / file_name


class ApiError(RuntimeError):
    """One exception type for every failed call.

    A failing call should say which method failed, with what status, and what the server
    actually replied - guessing from a bare 422 costs far more than the extra lines.
    """

    def __init__(self, method: str, message: str, response: httpx.Response) -> None:
        super().__init__(
            f"[API:{method}] {message}: {response.status_code} {response.reason_phrase}\n{response.text}"
        )


class ApiRequests:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=60.0, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    @property
    def base_url(self) -> str:
        return settings.api_url

    @staticmethod
    def auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", **JSON_HEADERS}

    def _get_with_retry(
        self, url: str, headers: dict[str, str], *, label: str, attempts: int = 3
    ) -> httpx.Response:
        """GET with a linear backoff over TRANSIENT_STATUSES. The caller decides what a final
        failure means, so this returns the response instead of raising."""
        response = self._client.get(url, headers=headers)
        for attempt in range(1, attempts):
            if response.status_code not in TRANSIENT_STATUSES:
                break
            log.info("[%s] transient %s, retry %s/%s", label, response.status_code, attempt, attempts - 1)
            time.sleep(2 * attempt)
            response = self._client.get(url, headers=headers)
        return response

    @staticmethod
    def _unwrap_pub_list(parsed: Any, label: str) -> list[Any]:
        """Some endpoints return a bare array, others wrap it in {"data": [...]}."""
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
            return parsed["data"]
        raise ValueError(f"[API:{label}] expected an array or {{data: array}}, got {str(parsed)[:200]}")

    def handle_token_file(self, file_name: str, token: str, overwrite: bool = False) -> None:
        file_path = resolve_token_file_path(file_name)

        if not file_path.exists():
            if "accounts" in file_path.parts:
                raise FileNotFoundError(f"{file_path} does not exist - provision the account first")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(json.dumps({"token": token}, indent=2), encoding="utf-8")
            return

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.info("Invalid JSON in %s, recreating it", file_path)
            file_path.write_text(json.dumps({"token": token}, indent=2), encoding="utf-8")
            return

        if not data.get("token") or overwrite:
            data["token"] = token
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def verify_token(self, token_file: str) -> str | bool:
        """Return a usable cached token, or False when a full login is needed."""
        file_path = resolve_token_file_path(token_file)
        if not file_path.exists():
            return False

        token = json.loads(file_path.read_text(encoding="utf-8")).get("token")
        if not token:
            return False

        if not self.token_is_fresh(token):
            return self.refresh_token(token, token_file)

        return token

    @staticmethod
    def token_is_fresh(token: str) -> bool:
        """Decode the JWT payload locally and check its `exp` claim.

        A JWT is three base64url segments joined by dots; the middle one is the payload. No
        signature check - this reads our own token's expiry, it does not trust it.
        """
        try:
            payload_segment = token.split(".")[1]
            padded = payload_segment.replace("-", "+").replace("_", "/")
            padded += "=" * ((4 - len(padded) % 4) % 4)
            payload = json.loads(base64.b64decode(padded).decode("utf-8"))
        except Exception:
            return False

        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return False
        return exp * 1000 - time.time() * 1000 > TOKEN_EXPIRY_LEEWAY_MS

    def refresh_token(self, token: str, token_file: str) -> str | bool:
        """Exchange a near-expired token for a fresh one. False means "fall back to login"."""
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/auth/refresh", headers=self.auth_headers(token)
        )
        if not response.is_success:
            return False
        new_token = response.json()["token"]["access_token"]
        self.handle_token_file(token_file, new_token, overwrite=True)
        return new_token

    def login(self, email: str, password: str, file: str | None = None) -> str:
        """Sign in and return a JWT.

        Pass `file` to use the disk cache; omit it to force a real login, which is what the
        role-parametrized tests do when switching users. The empty cookie in the headers clears
        any server-side session, so the response carries a clean token.
        """
        if file:
            cached = self.verify_token(file)
            if isinstance(cached, str):
                return cached

        response = self._client.post(
            f"{self.base_url}/api/v1/internal/2fa/auth/login",
            headers={**JSON_HEADERS, "cookie": f"{settings.token_cookie}="},
            json={"email": email, "password": password, "remember": False},
        )
        if not response.is_success:
            raise ApiError("login", "failed to login", response)

        new_token = response.json()["token"]["access_token"]
        if file:
            self.handle_token_file(file, new_token, overwrite=True)
        return new_token

    def get_teams(self, token: str) -> list[dict]:
        response = self._get_with_retry(
            f"{self.base_url}/api/v1/public/teams", self.auth_headers(token), label="get_teams"
        )
        if not response.is_success:
            raise ApiError("get_teams", "failed to fetch teams", response)
        return self._unwrap_pub_list(response.json(), "get_teams")

    def get_personal_teams(self, token: str) -> list[dict]:
        """Personal inboxes live in a separate endpoint and are absent from /teams."""
        response = self._client.get(
            f"{self.base_url}/api/v1/public/teams/personal", headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("get_personal_teams", "failed to fetch personal teams", response)
        return self._unwrap_pub_list(response.json(), "get_personal_teams")

    def get_team_id_by_name(self, token: str, name: str = "Main inbox") -> int:
        teams = self.get_teams(token)
        team = next((candidate for candidate in teams if candidate.get("name") == name), None)
        if not team:
            found = ", ".join(str(candidate.get("name")) for candidate in teams)
            raise ValueError(f'no inbox named "{name}" - found: {found}')
        return team["id"]

    def get_team_id(self, token: str, business_number: str) -> int:
        """Find an inbox by the phone number attached to it, personal inboxes included."""
        formatted = format_phone_number_to_formatted_number(business_number)

        def matches(team: dict) -> bool:
            return (team.get("number") or {}).get("formattedNumber") == formatted

        team = next((t for t in self.get_teams(token) if matches(t)), None)
        if not team:
            team = next((t for t in self.get_personal_teams(token) if matches(t)), None)
        if not team:
            raise AssertionError(f'no inbox for "{business_number}" (normalized "{formatted}")')
        return team["id"]

    def send_message(self, token: str, team_id: int, phone_number: str, message: str) -> dict:
        response = self._client.post(
            f"{self.base_url}/api/v1/public/messages",
            headers=self.auth_headers(token),
            json={"number": phone_number, "message": message, "team_id": team_id},
        )
        if not response.is_success:
            raise ApiError("send_message", "failed to send message", response)
        return response.json()

    def send_message_recipient(self, phone_number: str, message: str) -> None:
        """Send from the shared old account, used to send START and opt a number back in."""
        old_token = self.login(settings.old_account_email, settings.old_account_pass, "old.json")
        team_id = self.get_team_id(old_token, settings.old_account_phone)
        self.send_message(old_token, team_id, phone_number, message)

    def wait_recipient_opted_in(self, token: str, phone: str, max_attempts: int = 20) -> None:
        """Opting back in is asynchronous on the backend, so this polls for the flag to clear."""
        for _ in range(max_attempts):
            if not self.check_if_recipient_opted_out(token, phone):
                return
            time.sleep(3)
        raise AssertionError(f'"{phone}" is still opted out after {max_attempts * 3}s')

    def get_tags(self, token: str) -> dict:
        response = self._client.get(f"{self.base_url}/api/v1/public/tags", headers=self.auth_headers(token))
        if not response.is_success:
            raise ApiError("get_tags", "failed to fetch tags", response)
        return response.json()

    def tags(self, token: str, label: str) -> dict:
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/tags", headers=self.auth_headers(token), json={"label": label}
        )
        if not response.is_success:
            raise ApiError("tags", "failed to create a tag", response)
        return response.json()

    def delete_tag(self, token: str, tag_id: int) -> dict:
        response = self._client.delete(
            f"{self.base_url}/api/v1/public/tags/{tag_id}", headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("delete_tag", "failed to delete a tag", response)
        return response.json()

    def delete_all_tags(self, token: str) -> None:
        for tag in self.get_tags(token).get("data", []):
            self.delete_tag(token, tag["id"])

    def get_tag_id(self, token: str, tag_name: str) -> int:
        """The API is inconsistent about whether the name is in "label" or in "name"."""
        for tag in self.get_tags(token).get("data", []):
            if tag_name in (tag.get("label"), tag.get("name")):
                return tag["id"]
        raise ValueError(f'tag "{tag_name}" not found')

    def add_tag_to_contact(self, token: str, tag: str, contact_numbers: list[str]) -> dict:
        """Attach an existing tag to contacts identified by phone number.

        This is the endpoint behind the bulk UI action, hence the filter and search fields:
        they describe "which contacts", and bulk_all=False means "the ids listed here".
        """
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/contacts/tags",
            headers=self.auth_headers(token),
            json={
                "bulk_all": False,
                "contact_ids": self.get_contact_id(token, contact_numbers),
                "filtersList": [],
                "search": "",
                "tags": [{"id": self.get_tag_id(token, tag), "actionsProps": None, "label": tag, "name": tag}],
            },
        )
        if not response.is_success:
            raise ApiError("add_tag_to_contact", "failed to tag contacts", response)
        return response.json()

    def get_contacts(self, token: str) -> dict:
        response = self._client.get(
            f"{self.base_url}/api/v1/public/contacts?length=10&page=1", headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("get_contacts", "failed to get contacts", response)
        return response.json()

    def find_contacts(self, token: str, term: str) -> dict:
        """The search endpoint returns {"results": [...]}, not {"data": [...]}."""
        response = self._client.get(
            f"{self.base_url}/api/v1/public/contacts/search?limit=50&term={term}",
            headers=self.auth_headers(token),
        )
        if not response.is_success:
            raise ApiError("find_contacts", "failed to find contacts", response)
        return response.json()

    def get_contact_id(self, token: str, contact_numbers: list[str] | str) -> list[int]:
        numbers = [contact_numbers] if isinstance(contact_numbers, str) else contact_numbers
        contacts = self.get_contacts(token).get("data", [])
        contact_ids = []
        for number in numbers:
            formatted = format_phone_number_to_formatted_number(number)
            found = next((c for c in contacts if c.get("formatted_number") == formatted), None)
            if not found:
                raise ValueError(f'contact with number "{number}" not found')
            contact_ids.append(found["id"])
        return contact_ids

    def create_contact(self, token: str, contact: NewContact) -> dict:
        """The endpoint takes query parameters, not a JSON body."""
        query = [f"number={only_digits(contact.phone)}"]
        if contact.first_name:
            query.append(f"first_name={contact.first_name}")
        if contact.last_name:
            query.append(f"last_name={contact.last_name}")
        if contact.email:
            query.append("email=" + contact.email.replace("+", "%2B").replace("@", "%40"))

        response = self._client.post(
            f"{self.base_url}/api/v1/public/contacts?" + "&".join(query), headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("create_contact", f"failed to create contact {contact.phone}", response)
        return response.json()

    def check_if_recipient_opted_out(self, token: str, phone: str) -> bool:
        """An opted-out contact cannot be messaged, which breaks any test that tries.

        The search is fuzzy and returns near-matches, so the result is confirmed on the last
        ten digits rather than trusted outright.
        """
        digits = only_digits(phone)
        tail = digits[-10:]
        results = self.find_contacts(token, digits).get("results", [])
        contact = next(
            (
                r
                for r in results
                if only_digits(str(r.get("number") or r.get("national_number") or "")).endswith(tail)
            ),
            None,
        )
        return bool(contact and contact.get("opt_out_at"))

    def get_custom_fields(self, token: str) -> dict:
        response = self._client.get(
            f"{self.base_url}/api/v1/public/custom-fields/fields", headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("get_custom_fields", "failed to get custom fields", response)
        return response.json()

    def add_custom_field(self, token: str, custom_field: NewCustomField) -> dict:
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/custom-fields/field",
            headers=self.auth_headers(token),
            json=custom_field.model_dump(),
        )
        if not response.is_success:
            raise ApiError("add_custom_field", "failed to add a custom field", response)
        return response.json()

    def delete_custom_field(self, token: str, custom_field_id: str) -> dict:
        response = self._client.delete(
            f"{self.base_url}/api/v1/internal/custom-fields/field/{custom_field_id}",
            headers=self.auth_headers(token),
        )
        if not response.is_success:
            raise ApiError("delete_custom_field", "failed to delete a custom field", response)
        return response.json()

    def delete_all_custom_fields(self, token: str) -> None:
        """The four built-in fields have no id, which is how they are skipped."""
        for custom_field in self.get_custom_fields(token).get("data", []):
            if custom_field.get("id"):
                self.delete_custom_field(token, custom_field["id"])

    def update_contact_custom_field(
        self, token: str, contact_phone: str, custom_field_name: str, value: str
    ) -> dict:
        """Three lookups first: the field (name -> key), the contact (phone -> id), then the
        update. The API addresses fields by an opaque key, not by their display name."""
        custom_fields = self.get_custom_fields(token)["data"]
        contact_id = self.find_contacts(token, only_digits(contact_phone))["results"][0]["id"]
        custom_key = next(f for f in custom_fields if f["name"] == custom_field_name)["key"]

        response = self._client.put(
            f"{self.base_url}/api/v1/public/contacts/{contact_id}/custom-fields"
            f"?custom_field_key={custom_key}&value={value.replace(' ', '%20')}",
            headers=self.auth_headers(token),
        )
        if not response.is_success:
            raise ApiError("update_contact_custom_field", "failed to set a custom field", response)
        return response.json()

    def get_members(self, token: str) -> list[dict]:
        response = self._client.get(
            f"{self.base_url}/api/v1/public/organization/members", headers=self.auth_headers(token)
        )
        if not response.is_success:
            raise ApiError("get_members", "failed to fetch members", response)
        return response.json()

    def update_user_role(self, token: str, member_id: int, role: str, permissions: dict) -> None:
        """This is what makes the role-parametrized tests possible.

        The endpoint replaces the whole permission set rather than patching it, so the caller
        passes a complete one from constants/default_role_permissions.py.

        Two fields are sent fixed: member_id is who inherits their conversations, and 0 means
        nobody; remove_seat stays 0 so the paid seat survives, since dropping it would change
        the account's billing.
        """
        response = self._client.put(
            f"{self.base_url}/api/v1/internal/organization/members/{member_id}",
            headers=self.auth_headers(token),
            json={
                "role": role,
                "permissions": permissions,
                "member_id": 0,
                "remove_seat": 0,
                "use_organization_settings": False,
            },
        )
        if not response.is_success:
            raise ApiError("update_user_role", "failed to update a role", response)

    def update_global_permissions(self, token: str, role: str, permissions: dict) -> None:
        """Reset the organization-wide defaults for a role.

        The accounts are permanent, so a test that narrowed a role has to put it back or it
        poisons every later run.
        """
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/organization/permissions/save",
            headers=self.auth_headers(token),
            json={"role": role, "permissions": permissions},
        )
        if not response.is_success:
            raise ApiError("update_global_permissions", f"failed to reset {role} defaults", response)

    def add_member_to_inbox(self, token: str, inbox: str, email: str) -> dict:
        """The endpoint wants the member id as a string, not as a number."""
        team_id = self.get_team_id_by_name(token, inbox)
        member_id = next(m for m in self.get_members(token) if m["email"] == email)["id"]
        response = self._client.post(
            f"{self.base_url}/api/v1/internal/teams/{team_id}/members",
            headers=self.auth_headers(token),
            json={"members": [{"id": str(member_id)}]},
        )
        if not response.is_success:
            raise ApiError("add_member_to_inbox", "failed to add a member to an inbox", response)
        return response.json()
