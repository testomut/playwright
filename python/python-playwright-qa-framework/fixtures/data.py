"""Cleanup and seeded test data.

The accounts are permanent: nothing registers a fresh organization per test, because sign-up
is slow and burns phone numbers. The price is that every test inherits whatever the previous
one left behind, so cleanup is not housekeeping - it is what makes the suite repeatable.

clear_account therefore runs twice: before the test, so it starts from a known state even if
the previous run crashed, and after it, so it leaves one.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

import pytest

from src.config import settings
from src.constants.default_role_permissions import (
    default_admin_permissions,
    default_manager_permissions,
    default_member_permissions,
)
from src.constants.functions import format_phone_number
from src.types.models import NewCustomField, RegistrationData
from src.utils.api_requests import ApiRequests

log = logging.getLogger(__name__)


def restore_step(name: str, step: Callable[[], object]) -> None:
    """Run one cleanup step, swallowing any failure.

    Cleanup must never fail the test that asked for it. A test that passed but whose teardown
    hit a 500 while deleting tags is a passing test with a noisy log; turning that into a
    failure would hide real regressions behind infrastructure noise.

    The step is a callable rather than a value, so it only runs inside the try - which is why
    every call site wraps it in a lambda.
    """
    try:
        step()
    except Exception as error:
        log.info("Cleanup [%s] failed: %s", name, error)


def ensure_member_in_main_inbox(
    api_request: ApiRequests, user_details: RegistrationData, main_inbox_name: str = "Main inbox"
) -> None:
    """Put the seeded member back into the main inbox if a test removed them.

    Removing a member from an inbox is not undone anywhere else, and on a permanent account
    that member can end up with no inbox at all. Every fixture that later signs in as them then
    waits forever for an inbox list that never arrives.

    Needs the owner's token: a member cannot grant themselves access.
    """
    if not user_details.member or not user_details.token:
        return

    teams = api_request.get_teams(user_details.token)
    main = next((team for team in teams if team.get("name") == main_inbox_name), None)
    seeded = next(
        (m for m in api_request.get_members(user_details.token) if m["email"] == user_details.member.email),
        None,
    )
    if not main or not seeded:
        return
    if int(seeded["id"]) in [int(member_id) for member_id in main.get("member_ids") or []]:
        return

    log.info("Member %s lost access to %s, adding it back", user_details.member.email, main_inbox_name)
    api_request.add_member_to_inbox(user_details.token, main_inbox_name, user_details.member.email)


@pytest.fixture
def clear_account(
    api_request: ApiRequests, user_details: RegistrationData, authorized_token: str
) -> Iterator[None]:
    """Reset the permanent worker account before and after the test.

    The try/finally around the yield is what makes a failing test still clean up after itself.
    """
    token = user_details.token

    def cleanup(phase: str) -> None:
        restore_step(f"{phase}/tags", lambda: api_request.delete_all_tags(token))
        restore_step(f"{phase}/custom_fields", lambda: api_request.delete_all_custom_fields(token))
        restore_step(f"{phase}/member_inbox", lambda: ensure_member_in_main_inbox(api_request, user_details))

        if phase == "setup":

            def restore_global_permissions() -> None:
                api_request.update_global_permissions(token, "admin", default_admin_permissions())
                api_request.update_global_permissions(token, "manager", default_manager_permissions())
                api_request.update_global_permissions(token, "member", default_member_permissions())

            restore_step(f"{phase}/role_defaults", restore_global_permissions)

    cleanup("setup")
    try:
        yield
    finally:
        cleanup("teardown")


@pytest.fixture
def clear_member_account(
    api_request: ApiRequests, user_details: RegistrationData, authorized_token: str
) -> Iterator[None]:
    """Demote the seeded member back to `member` after a role-parametrized test.

    Teardown only, so the yield comes first. Pairs with oauth_by_role, which promoted them.
    """
    yield
    if not user_details.member:
        return

    def restore_role() -> None:
        members = api_request.get_members(user_details.token)
        member_id = next((m["id"] for m in members if m["email"] == user_details.member.email), None)
        if member_id:
            api_request.update_user_role(user_details.token, member_id, "member", default_member_permissions())

    restore_step("teardown/member_role", restore_role)


@pytest.fixture
def tag_for_test(
    api_request: ApiRequests, user_details: RegistrationData, authorized_token: str, clear_account: None
) -> str:
    """Seed exactly one tag and return its name.

    Wiping first, rather than trusting the account to be empty, lets a test assert "there is
    exactly one tag" without depending on what ran before it.
    """
    api_request.delete_all_tags(user_details.token)
    new_tag = "tagTest"
    api_request.tags(user_details.token, new_tag)
    return new_tag


@pytest.fixture
def custom_field_for_test(
    api_request: ApiRequests, user_details: RegistrationData, authorized_token: str, clear_account: None
) -> dict[str, str]:
    """Seed one custom field and fill it in on the shared account's contact."""
    test_data = {"name": "Qa Trig", "value": "qa tests"}

    api_request.delete_all_custom_fields(user_details.token)
    api_request.add_custom_field(
        user_details.token, NewCustomField(name=test_data["name"], type="text", visible=False)
    )
    api_request.update_contact_custom_field(
        user_details.token,
        format_phone_number(settings.old_account_phone),
        test_data["name"],
        test_data["value"],
    )
    return test_data
