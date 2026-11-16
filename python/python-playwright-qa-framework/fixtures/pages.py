"""Page object and sign-in fixtures.

`start` only performs the side effect - signing in and opening the seeded conversation - and
each page object is its own fixture, so a test asks for exactly what it uses:

    def test_x(start, tags_page, api_request): ...

pytest builds only the fixtures a test names, which is cheaper than constructing forty page
objects for a test that touches one.

`page` and `context` come from pytest-playwright and are function-scoped: a fresh browser
context per test is what keeps tests isolated.
"""

from __future__ import annotations

import logging

import pytest
from playwright.sync_api import BrowserContext, Page

from src.config import settings
from src.constants.functions import format_phone_number
from src.pages.contacts_page import ContactsPage
from src.pages.conversations_page import ConversationsPage
from src.pages.custom_fields_page import CustomFieldsPage
from src.pages.saved_replies_page import SavedRepliesPage
from src.pages.settings_page import SettingsPage
from src.pages.tags_page import TagsPage
from src.types.models import RegistrationData
from src.utils.api_requests import ApiRequests
from src.utils.custom_commands import CustomCommands

log = logging.getLogger(__name__)


@pytest.fixture
def custom(page: Page, context: BrowserContext) -> CustomCommands:
    """Bare CustomCommands, for tests that need wrapped_test_step but no page object."""
    return CustomCommands(page, context)


@pytest.fixture
def conversations_page(page: Page, context: BrowserContext) -> ConversationsPage:
    return ConversationsPage(page, context)


@pytest.fixture
def contacts_page(page: Page, context: BrowserContext) -> ContactsPage:
    return ContactsPage(page, context)


@pytest.fixture
def settings_page(page: Page, context: BrowserContext) -> SettingsPage:
    return SettingsPage(page, context)


@pytest.fixture
def tags_page(page: Page, context: BrowserContext, api_request: ApiRequests) -> TagsPage:
    """TagsPage also seeds tags over the API, so it gets the shared client."""
    return TagsPage(page, context, api_request)


@pytest.fixture
def custom_fields_page(page: Page, context: BrowserContext) -> CustomFieldsPage:
    return CustomFieldsPage(page, context)


@pytest.fixture
def saved_replies_page(page: Page, context: BrowserContext) -> SavedRepliesPage:
    return SavedRepliesPage(page, context)


@pytest.fixture
def start(
    conversations_page: ConversationsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    old_account_token: str,
    authorized_token: str,
) -> RegistrationData:
    """Sign in as the worker's owner account and open the seeded conversation.

    The opt-out repair in the middle is not optional. Messaging is consent-based: a number that
    replied STOP cannot be messaged, and several tests do exactly that as part of their
    scenario. The accounts are permanent, so that state survives into later runs - both
    directions are checked and a START clears it. Without this the failure lands in a
    completely unrelated test.

    The composer is emptied at the end because the app persists drafts per conversation.
    """
    old_account_phone = format_phone_number(settings.old_account_phone)

    conversations_page.oauth_with_token(user_details.token)

    if api_request.check_if_recipient_opted_out(user_details.token, old_account_phone):
        api_request.send_message_recipient(user_details.business_number, "START")
        api_request.wait_recipient_opted_in(user_details.token, old_account_phone)

    if api_request.check_if_recipient_opted_out(old_account_token, user_details.business_number):
        team_id = api_request.get_team_id_by_name(user_details.token, "Main inbox")
        api_request.send_message(user_details.token, team_id, old_account_phone, "START")
        api_request.wait_recipient_opted_in(old_account_token, user_details.business_number)

    conversations_page.select_inbox("Main inbox")
    conversations_page.select_conversation(old_account_phone, phone=True)
    conversations_page.clear_input_message()
    return user_details


@pytest.fixture
def start_old_account(
    conversations_page: ConversationsPage,
    user_details: RegistrationData,
    old_account_token: str,
    authorized_token: str,
) -> str:
    """Sign in as the shared account that holds the large seeded data set.

    Used by tests that need hundreds of rows - pagination, sorting, "select all". Building that
    much data per test would be far too slow.

    The catch: this account is shared by every worker, so a test using it must only read.
    """
    conversations_page.oauth_with_token(old_account_token)
    conversations_page.select_inbox("Chats")
    conversations_page.select_conversation(user_details.business_number, phone=True)
    conversations_page.close_plan_credits_exceeded()
    return old_account_token
