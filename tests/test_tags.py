"""Tag tests.

How a test is put together:

    def test_create_tag_already_existing(     <- the name shown in the report
        start, clear_account,                 <- fixtures, in the order they must run
        tag_for_test, tags_page, custom,
    ):
        '''Tags: Create Tag: Already Existing'''   <- the case title
        with custom.wrapped_test_step("1. ..."):              <- a named, timed step
            ...

Setup dependencies should be expressed explicitly in fixtures; argument order alone is not a dependency contract.
"""

from __future__ import annotations

import pytest

from src.config import settings
from src.constants.functions import (
    format_phone_number,
    format_phone_number_to_formatted_number,
    format_phone_number_to_only_numbers,
)
from src.pages.tags_page import TagsPage
from src.types.models import NewContact, RegistrationData, Role, TagData
from src.utils.api_requests import ApiRequests
from src.utils.custom_commands import CustomCommands
from src.utils.parametrization_helpers import ROLES, oauth_by_role

OLD_ACCOUNT_PHONE = format_phone_number(settings.old_account_phone)
OLD_ACCOUNT_PHONE_SHORT_CODE = format_phone_number_to_only_numbers(settings.old_account_phone_short_code)

LONG_TAG_NAME = "Long tag name With 51 symbol Long tag name 51 symbo"


def test_create_tag_already_existing(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    custom: CustomCommands,
) -> None:
    """Tags: Create Tag: Already Existing"""
    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])

    with custom.wrapped_test_step("2. Create a new tag with name that already has existing tag"):
        tags_page.create_tag_with_error(tag_for_test)
        tags_page.verify_error("exist")
        tags_page.click_cancel_button()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])


def test_search_tags(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Search Tags"""
    test_tag = "Test Tag"
    api_request.tags(user_details.token, test_tag)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(
            2, [TagData(tag_name=tag_for_test, contact="0"), TagData(tag_name=test_tag, contact="0")]
        )

    with custom.wrapped_test_step("2. Search Tag"):
        tags_page.use_search(test_tag)
        tags_page.verify_tags_list(1, [TagData(tag_name=test_tag, contact="0")])


def test_open_tags_contacts(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tag`s Contacts: Open Tag`s Contacts"""
    api_request.add_tag_to_contact(
        user_details.token, tag_for_test, [OLD_ACCOUNT_PHONE, OLD_ACCOUNT_PHONE_SHORT_CODE]
    )

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="2")])

    with custom.wrapped_test_step("2. Select the tag"):
        tags_page.select_tag(tag_for_test)
        tags_page.verify_tag_contacts_list([OLD_ACCOUNT_PHONE_SHORT_CODE, OLD_ACCOUNT_PHONE])


def test_sort_tags(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Sort Tags"""
    tags_page.create_a_lot_tags(2, "Tag", user_details.token)
    api_request.add_tag_to_contact(
        user_details.token, tag_for_test, [OLD_ACCOUNT_PHONE, OLD_ACCOUNT_PHONE_SHORT_CODE]
    )

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(
            3,
            [
                TagData(tag_name="Tag1", contact="0"),
                TagData(tag_name="Tag0", contact="0"),
                TagData(tag_name=tag_for_test, contact="2"),
            ],
        )

    with custom.wrapped_test_step("2. Sort Tags"):
        tags_page.sort_tags(
            "Name",
            3,
            [
                TagData(tag_name=tag_for_test, contact="2"),
                TagData(tag_name="Tag1", contact="0"),
                TagData(tag_name="Tag0", contact="0"),
            ],
        )
        tags_page.sort_tags(
            "Contacts",
            3,
            [
                TagData(tag_name=tag_for_test, contact="2"),
                TagData(tag_name="Tag0", contact="0"),
                TagData(tag_name="Tag1", contact="0"),
            ],
        )


def test_filter_tags(
    start_old_account: str,
    tags_page: TagsPage,
    custom: CustomCommands,
) -> None:
    """Tags: Filter Tags"""
    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.set_pagination_tags(10)
        tags_page.verify_tags_list(10)

    for pagination in (25, 50, 100):
        with custom.wrapped_test_step(f"Filter Tags {pagination} on page"):
            tags_page.set_pagination_tags(pagination)
            tags_page.verify_tags_list(pagination)


def test_search_for_tags_contacts(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tag`s Contacts: Search for Tag`s Contacts"""
    api_request.add_tag_to_contact(
        user_details.token, tag_for_test, [OLD_ACCOUNT_PHONE, OLD_ACCOUNT_PHONE_SHORT_CODE]
    )
    old_phone = format_phone_number_to_formatted_number(OLD_ACCOUNT_PHONE)
    short_code = format_phone_number_to_formatted_number(OLD_ACCOUNT_PHONE_SHORT_CODE)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="2")])

    with custom.wrapped_test_step("2. Select the tag"):
        tags_page.select_tag(tag_for_test)
        tags_page.verify_tag_contacts_list([old_phone, short_code])

    with custom.wrapped_test_step("3. Search for Tag's Contacts"):
        tags_page.use_search(old_phone)
        tags_page.verify_tag_contacts_list([old_phone])


def test_sort_tags_contacts(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tag`s Contacts: Sort Tag`s Contacts"""
    first = NewContact(
        phone=format_phone_number("2025550001"),
        first_name="Kait1",
        last_name="Lambert1",
        email="contact1@example.test",
    )
    second = NewContact(
        phone=format_phone_number("2025550002"),
        first_name="Kait2",
        last_name="Lambert2",
        email="contact2@example.test",
    )
    api_request.create_contact(user_details.token, first)
    api_request.create_contact(user_details.token, second)
    api_request.add_tag_to_contact(user_details.token, tag_for_test, [first.phone, second.phone])

    first_formatted = format_phone_number_to_formatted_number(first.phone)
    second_formatted = format_phone_number_to_formatted_number(second.phone)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="2")])

    with custom.wrapped_test_step("2. Select the tag"):
        tags_page.select_tag(tag_for_test)
        tags_page.verify_tag_contacts_list([first_formatted, second_formatted])

    with custom.wrapped_test_step("3. Sort Tag's Contacts"):
        tags_page.sort_contacts("Name", "to high")
        tags_page.verify_tag_contacts_list([second_formatted, first_formatted])
        tags_page.sort_contacts("Phone", "to high")
        tags_page.verify_tag_contacts_list([first_formatted, second_formatted])
        tags_page.sort_contacts("Email", "to low")
        tags_page.verify_tag_contacts_list([first_formatted, second_formatted])


def test_contact_name_does_not_overlap_the_number(
    start: RegistrationData,
    clear_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tag`s Contacts: Contact Name Doesn`t Overlap the Number (Long First and Last Name)"""
    contact = NewContact(
        phone=format_phone_number("2025550003"),
        first_name="KaitLongLongFirstName",
        last_name="LambertLongLongLastName",
        email="contact1@example.test",
    )
    api_request.create_contact(user_details.token, contact)
    api_request.add_tag_to_contact(user_details.token, tag_for_test, [contact.phone])

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="1")])

    with custom.wrapped_test_step("2. Verify 3 Dots On Contact's Name"):
        tags_page.select_tag(tag_for_test)
        tags_page.verify_3_dots_contacts_name([f"{contact.first_name} {contact.last_name}"])


def test_tags_pagination(
    start_old_account: str,
    tags_page: TagsPage,
    custom: CustomCommands,
) -> None:
    """Tags: Tags Pagination"""
    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.set_pagination_tags(10)
        tags_page.verify_tags_list(10)
        tags_page.verify_from_tags_to_on_page("1-10")

    with custom.wrapped_test_step("2. Click to Next Page"):
        tags_page.click_next_page(3)
        tags_page.verify_tags_list(10)
        tags_page.verify_from_tags_to_on_page("31-40")


@pytest.mark.parametrize("role", ROLES)
def test_create_tag_by_role(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Create Tag"""
    oauth_by_role(api_request, user_details, role, tags_page)
    test_tag = "Test Tag"

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()

    with custom.wrapped_test_step("2. Create Tag"):
        tags_page.create_tag(test_tag)
        tags_page.verify_tags_list(1, [TagData(tag_name=test_tag, contact="0")])


@pytest.mark.parametrize("role", ROLES)
def test_edit_tag_by_role(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Edit Tag"""
    oauth_by_role(api_request, user_details, role, tags_page)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])

    with custom.wrapped_test_step("2. Edit Tag"):
        tags_page.action_on_3_dots(tag_for_test, "Edit", tag_for_test)
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])


@pytest.mark.parametrize("role", ROLES)
def test_delete_tag_by_role(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Delete Tag"""
    oauth_by_role(api_request, user_details, role, tags_page)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])

    with custom.wrapped_test_step("2. Delete Tag"):
        tags_page.action_on_3_dots(tag_for_test, "Delete")
        tags_page.verify_tags_list(0, [])


@pytest.mark.parametrize("role", ROLES)
def test_bulk_delete_tags_by_role(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    tag_for_test: str,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Bulk Delete Tags"""
    oauth_by_role(api_request, user_details, role, tags_page)
    tags_page.create_a_lot_tags(2, "Tag", user_details.token)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(
            3,
            [
                TagData(tag_name="Tag1", contact="0"),
                TagData(tag_name="Tag0", contact="0"),
                TagData(tag_name=tag_for_test, contact="0"),
            ],
        )

    with custom.wrapped_test_step("2. Delete Tags by bulk"):
        tags_page.delete_some_tags_by_bulk(["Tag1", "Tag0"])
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])


@pytest.mark.parametrize("role", ROLES)
def test_edit_tag_longer_than_50_characters_by_role(
    role: Role,
    start: RegistrationData,
    tag_for_test: str,
    clear_member_account: None,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Edit Tag: Longer than 50 Characters"""
    oauth_by_role(api_request, user_details, role, tags_page)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()
        tags_page.verify_tags_list(1, [TagData(tag_name=tag_for_test, contact="0")])

    with custom.wrapped_test_step("2. Edit Tag"):
        tags_page.rename_tag(tag_for_test, LONG_TAG_NAME, update=False)
        tags_page.verify_warning("Cannot be longer than 50 characters")
        tags_page.click_update_button()
        tags_page.verify_tags_list(1, [TagData(tag_name=LONG_TAG_NAME[:-1], contact="0")])


@pytest.mark.parametrize("role", ROLES)
def test_create_tag_longer_than_50_characters_by_role(
    role: Role,
    start: RegistrationData,
    clear_account: None,
    clear_member_account: None,
    tags_page: TagsPage,
    api_request: ApiRequests,
    user_details: RegistrationData,
    custom: CustomCommands,
) -> None:
    """Tags: Create Tag: Longer than 50 Characters"""
    oauth_by_role(api_request, user_details, role, tags_page)

    with custom.wrapped_test_step("1. Go to Tags"):
        tags_page.open_tags_page()

    with custom.wrapped_test_step("2. Create Tag"):
        tags_page.create_tag_with_error(LONG_TAG_NAME, create=False)
        tags_page.verify_warning("Cannot be longer than 50 characters")
        tags_page.click_save_button()
        tags_page.verify_tags_list(1, [TagData(tag_name=LONG_TAG_NAME[:-1], contact="0")])
