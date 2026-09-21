"""Contacts page object.

The app has a two-level selection model, which these tests exercise directly:
  - tick individual rows              -> "You have selected 3 of ..."
  - tick the header checkbox          -> every row on the current page
  - then press "Select all contacts"  -> the whole filtered set, across pages
"""

from __future__ import annotations

from typing import ClassVar, Literal

from playwright.sync_api import BrowserContext, Page

from src.pages.base_page import BasePage
from src.types.models import CustomField

SelectedAmount = int | Literal["All", "Null"]

DEFAULT_CONTACT_FIELDS: list[CustomField] = [
    CustomField(name="First Name", type="First Name", show=True),
    CustomField(name="Last Name", type="Last Name", show=True),
    CustomField(name="Phone", type="Phone", show=True),
    CustomField(name="Email", type="Email", show=True),
]


class ContactsPage(BasePage):
    contact_list_selector = '[aria-label="ContactItemRow"]'
    selected_contacts_amount_selector = '[aria-label="TypographySelectedCountText"]'
    select_contact_selector = 'tbody [aria-label="Checkbox"]'
    select_all_contacts_button_selector = '[aria-label="ButtonSelectAllContacts"]'
    clear_selection_button_selector = '[aria-label="ButtonClearSelection"]'
    see_fields_button_selector = '[aria-label="ButtonSeeFields_Text"]'
    field_selector = '[aria-label="Field"]'

    field_type_selectors: ClassVar[dict[str, str]] = {
        "First Name": '[aria-label="FieldType_FirstName"]',
        "Last Name": '[aria-label="FieldType_LastName"]',
        "Phone": '[aria-label="FieldType_Phone"]',
        "Email": '[aria-label="FieldType_Email"]',
        "Owner": '[aria-label="FieldType_UserFilled"]',
        "Text": '[aria-label="FieldType_Text"]',
        "Number": '[aria-label="FieldType_Number"]',
        "Date": '[aria-label="FieldType_Date"]',
        "URL": '[aria-label="FieldType_Url"]',
        "Date & Time": '[aria-label="FieldType_DateAndTime"]',
    }

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def open_contacts_page(self) -> None:
        self.custom_click(self.open_contacts_page_selector)
        self.page.locator(self.contact_list_selector).first.wait_for(state="visible")

    def select_contacts(self, contacts: list[int]) -> None:
        """Tick rows by 1-based position. Ticking a ticked row unticks it.

        The checkbox selector is scoped to tbody so the header checkbox is not part of the
        set - otherwise position 1 would tick "select all" instead of the first row.
        """
        for contact in contacts:
            self.custom_click(self.page.locator(self.select_contact_selector).nth(contact - 1))

    def select_all_contacts(self) -> None:
        """Escalate from "this page" to "every contact in the filter".

        The button only appears once a full page is selected and there is more than one page.
        """
        self.click_if_element_present(self.select_all_contacts_button_selector)

    def clear_selected_all_contacts(self) -> None:
        self.custom_click(self.clear_selection_button_selector)

    def verify_contacts_amount(self, amount: SelectedAmount) -> None:
        """Three shapes, because the app renders three different things:

        3      -> "You have selected 3 of 120 contacts"
        "All"  -> "All 120 contacts are selected"
        "Null" -> the counter is not rendered at all
        """
        locator = self.page.locator(self.selected_contacts_amount_selector)

        if isinstance(amount, int):
            actual = locator.inner_text()
            assert f"You have selected {amount} of" in actual, (
                f"Expected {amount} selected, counter reads: {actual}"
            )
        elif amount == "Null":
            count = locator.count()
            assert count == 0, f"Expected no selection counter, found {count}"
        else:
            actual = locator.inner_text()
            assert "contacts are selected" in actual, f"Expected all contacts selected, counter reads: {actual}"

    def open_contact_info_by_number(self, number: int) -> None:
        """Open the three-dots menu of the Nth row (1-based)."""
        self.custom_click(self.dropdown_actions_selector, nth=number - 1)

    def verify_contact_custom_fields(self, fields: list[CustomField] | None = None) -> None:
        """Cross-check that a custom field created in settings surfaces on a contact.

        Only the first five fields are shown; anything beyond needs "See fields".
        """
        all_fields = [*DEFAULT_CONTACT_FIELDS, *(fields or [])]

        self.open_contact_info_by_number(1)
        self.custom_click(self.edit_button_selector)
        self.wait_spinner_loader()
        if len(all_fields) > len(DEFAULT_CONTACT_FIELDS):
            self.custom_click(self.see_fields_button_selector)

        for field in all_fields:
            row = self.page.locator(self.field_selector).filter(has_text=field.name)
            icons = row.locator(self.field_type_selectors[field.type]).count()
            assert icons == 1, f"{field.name}: expected one {field.type} icon, found {icons}"
