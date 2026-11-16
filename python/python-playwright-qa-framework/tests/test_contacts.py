"""Contact tests.

All three use `start_old_account`, the shared account with hundreds of contacts - "select all"
is only meaningful when there is more than one page. They are read-only, which is the
condition for using that shared account safely.

Rows 3, 4 and 5 are picked rather than the first ones because new contacts land at the top of
the list, so the lower rows are stable across runs.
"""

from __future__ import annotations

from src.pages.contacts_page import ContactsPage
from src.utils.custom_commands import CustomCommands


def test_select_some_contacts(
    start_old_account: str,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Select Some Contacts"""
    contacts_page.open_contacts_page()

    with custom.wrapped_test_step("1. Select a checkbox for any contact"):
        contacts_page.select_contacts([3, 4, 5])
        contacts_page.verify_contacts_amount(3)


def test_unselect_contacts(
    start_old_account: str,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Unselect Contacts"""
    contacts_page.open_contacts_page()

    with custom.wrapped_test_step("1. Select a checkbox for any contact"):
        contacts_page.select_contacts([3, 4, 5])
        contacts_page.verify_contacts_amount(3)

    with custom.wrapped_test_step("2. Unselect checkbox for any contact"):
        contacts_page.select_contacts([4, 5])
        contacts_page.verify_contacts_amount(1)


def test_clear_selection(
    start_old_account: str,
    contacts_page: ContactsPage,
    custom: CustomCommands,
) -> None:
    """Clear Selection"""
    contacts_page.open_contacts_page()

    with custom.wrapped_test_step("1. Select all contacts on the page"):
        contacts_page.select_contacts([3, 4, 5])
        contacts_page.verify_contacts_amount(3)

    with custom.wrapped_test_step('2. Click on "Select all contacts"'):
        contacts_page.select_all_contacts()
        contacts_page.verify_contacts_amount("All")

    with custom.wrapped_test_step('3. Click on "Clear selection" button'):
        contacts_page.clear_selected_all_contacts()
        contacts_page.verify_contacts_amount("Null")
