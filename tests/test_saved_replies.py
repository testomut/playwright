"""Saved reply tests.

One test, four roles. It builds a reply with every kind of content the editor supports - text,
emoji, attachment, merge field, shortened link - then flips visibility from "Myself only" to
"All members" and creates it.
"""

from __future__ import annotations

import time

import pytest

from src.pages.saved_replies_page import SavedRepliesPage
from src.types.models import RegistrationData, Role
from src.utils.api_requests import ApiRequests
from src.utils.custom_commands import CustomCommands
from src.utils.parametrization_helpers import ROLES, oauth_by_role


@pytest.mark.timeout(400)
@pytest.mark.parametrize("role", ROLES)
def test_create_saved_reply_with_all_members_visibility(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    saved_replies_page: SavedRepliesPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Create Saved Reply With 'All Members' Visibility"""
    oauth_by_role(api_request, user_details, role, saved_replies_page)

    stamp = int(time.time() * 1000)
    title = f"qa saved reply {stamp}"
    message = f"qa message {stamp}"

    with custom.wrapped_test_step("1. Navigate to Settings > Saved replies"):
        saved_replies_page.open_save_reply_page()

    with custom.wrapped_test_step("2. Click '+New reply' button"):
        saved_replies_page.open_new_reply_form()

    with custom.wrapped_test_step("3. Enter the title > add text, emoji, attachment, merge field and short link"):
        saved_replies_page.fill_saved_reply_form(
            title,
            message,
            emoji="grinning face",
            file="img",
            merge_field="First Name",
            url="https://example.com",
        )

    with custom.wrapped_test_step("4. Verify default visibility is 'Myself only'"):
        saved_replies_page.verify_saved_reply_visibility("Myself only")

    with custom.wrapped_test_step("5. Change visibility to 'All members'"):
        saved_replies_page.set_saved_reply_visibility("All members")

    with custom.wrapped_test_step("6. Click 'Create' button"):
        saved_replies_page.create_saved_reply(title)
