"""Custom-field scenarios parameterized by field type."""

from __future__ import annotations

import pytest

from src.pages.contacts_page import ContactsPage
from src.pages.custom_fields_page import CustomFieldsPage
from src.pages.settings_page import SettingsPage
from src.types.models import CustomField, RegistrationData
from src.utils.custom_commands import CustomCommands

DEFAULT_CUSTOM_FIELDS: list[CustomField] = [
    CustomField(name="First Name", type="Text", show=True),
    CustomField(name="Last Name", type="Text", show=True),
    CustomField(name="Phone Number", type="Text", show=True),
    CustomField(name="E-Mail Address", type="Text", show=True),
]


@pytest.mark.parametrize(
    "field_type",
    ["Number", "Text", "URL", "Date"],
    ids=["number", "text", "url", "date"],
)
def test_create_custom_field(
    field_type: str,
    clear_account: None,
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Create Custom Field"""
    with custom.wrapped_test_step("1. Setting -> Custom fields"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list(DEFAULT_CUSTOM_FIELDS)

    with custom.wrapped_test_step("2. Click to Create field"):
        new_field = custom_fields_page.create_field(
            CustomField(name="qa_custom_field_1", type=field_type, show=True)
        )
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, new_field])

    with custom.wrapped_test_step('3. Verify "Contacts" page'):
        contacts_page.open_contacts_page()
        contacts_page.verify_contact_custom_fields([new_field])


def test_create_custom_field_duplicate_name(
    clear_account: None,
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    custom: CustomCommands,
) -> None:
    """Create Custom Field (Duplicate Name/Key)"""
    with custom.wrapped_test_step("1. Setting -> Custom fields"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list(DEFAULT_CUSTOM_FIELDS)

    with custom.wrapped_test_step("2. Create custom field like existing custom field"):
        custom_fields_page.create_field(CustomField(name="First Name", type="Number", show=True))
        custom_fields_page.verify_help_text("Name already exists")


def test_edit_custom_field(
    clear_account: None,
    custom_field_for_test: dict[str, str],
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Edit Custom Field"""
    seeded = CustomField(name=custom_field_for_test["name"], type="Text", show=False)
    updated = CustomField(name="qa_custom_field_2", type="Number", show=True)

    with custom.wrapped_test_step("1. Open Custom Fields page"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, seeded])

    with custom.wrapped_test_step("2. Edit custom field"):
        custom_fields_page.edit_custom_field(seeded.name, updated)
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, updated])

    with custom.wrapped_test_step('3. Verify "Contacts" page'):
        contacts_page.open_contacts_page()
        contacts_page.verify_contact_custom_fields([updated])


def test_delete_custom_field(
    clear_account: None,
    custom_field_for_test: dict[str, str],
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Delete Custom Field"""
    seeded = CustomField(name=custom_field_for_test["name"], type="Text", show=False)

    with custom.wrapped_test_step("1. Open Custom Fields page"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, seeded])

    with custom.wrapped_test_step("2. Delete custom field"):
        custom_fields_page.delete_custom_field(seeded.name)
        custom_fields_page.verify_custom_fields_list(DEFAULT_CUSTOM_FIELDS)

    with custom.wrapped_test_step('3. Verify "Contacts" page'):
        contacts_page.open_contacts_page()
        contacts_page.verify_contact_custom_fields()


def test_search_custom_field(
    clear_account: None,
    custom_field_for_test: dict[str, str],
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    custom: CustomCommands,
) -> None:
    """Search Custom Field"""
    seeded = CustomField(name=custom_field_for_test["name"], type="Text", show=False)

    with custom.wrapped_test_step("1. Open Custom Fields page"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, seeded])

    with custom.wrapped_test_step("2. Search custom field"):
        custom_fields_page.search_custom_field(seeded.name)
        custom_fields_page.verify_custom_fields_list([seeded])


def test_custom_fields_counter(
    clear_account: None,
    start: RegistrationData,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    custom: CustomCommands,
) -> None:
    """Custom Fields Counter"""
    with custom.wrapped_test_step("1. Verify default counter"):
        settings_page.open_custom_fields_page()
        custom_fields_page.verify_custom_fields_list(DEFAULT_CUSTOM_FIELDS)
        custom_fields_page.verify_custom_fields_counter("1  - 4​of 4")

    with custom.wrapped_test_step("2. Create custom field"):
        new_field = custom_fields_page.create_field(
            CustomField(name="qa_custom_field_1", type="Number", show=True)
        )
        custom_fields_page.verify_custom_fields_list([*DEFAULT_CUSTOM_FIELDS, new_field])
        custom_fields_page.verify_custom_fields_counter("1  - 5​of 5")


def test_filter_custom_fields(
    start_old_account: str,
    settings_page: SettingsPage,
    custom_fields_page: CustomFieldsPage,
    custom: CustomCommands,
) -> None:
    """Filter Custom Fields (Show ...)"""
    with custom.wrapped_test_step("1. Verify default filter"):
        settings_page.open_custom_fields_page()
        custom_fields_page.set_view(10)
        custom_fields_page.verify_custom_fields_counter("1  - 10of 105")

    for view in (25, 50, 100):
        with custom.wrapped_test_step(f"Verify with filter {view}"):
            custom_fields_page.set_view(view)
            custom_fields_page.verify_custom_fields_counter(f"1  - {view}of 105")
