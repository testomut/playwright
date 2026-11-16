"""Custom fields page object.

Every organization starts with four built-in fields (First Name, Last Name, Phone Number,
E-Mail Address) that cannot be deleted and always sort first.
"""

from __future__ import annotations

from playwright.sync_api import BrowserContext, Page, expect

from src.pages.settings_page import SettingsPage
from src.types.models import CustomField


class CustomFieldsPage(SettingsPage):
    create_field_button_selector = '[aria-label="ButtonNewField"]'
    field_has_name_selector = '[placeholder="Enter name"]'
    type_name_dropdown_selector = '[aria-label="DropdownSelectField"]'
    type_name_option_selector = '[aria-label="DropdownList_Item"]'
    field_has_visible_selector = '[aria-label="Checkbox"]'
    submit_button_selector = '[aria-label="ButtonCreate"]'
    save_button_selector = '[aria-label="ButtonSave"]'
    field_name_label_selector = '[aria-label="TypographyCustomFieldName"]'
    field_type_label_selector = '[aria-label="TypographyCustomFieldType"]'
    not_show_in_conversations_selector = '[aria-label="TypographyEmptyCellText"]'
    custom_fields_list_selector = '[aria-label="TableBody"] [data-index]'
    dropdown_dots_selector = '[aria-label="DropdownActions"]'
    search_input_selector = '[placeholder="Search..."]'
    help_text_selector = '[aria-label="TypographyError"]'
    toolbox_center_selector = '[aria-label="Pagination"]'

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def create_field(self, field: CustomField, create: bool = True) -> CustomField:
        """Return the field so the test can reuse it in the assertion."""
        self.custom_click(self.create_field_button_selector)
        self.custom_fill(self.field_has_name_selector, field.name)
        self.custom_click(self.type_name_dropdown_selector)
        self.custom_click(self.type_name_option_selector, has_text=field.type)
        if field.show:
            self.custom_click(self.field_has_visible_selector)
        if create:
            self.custom_click(self.submit_button_selector)
            self.wait_spinner_loader()
        return field

    def edit_custom_field(self, name: str, new_data: CustomField) -> None:
        field = self.page.locator(self.custom_fields_list_selector, has_text=name)
        field.locator(self.dropdown_dots_selector).click()
        self.custom_click(self.edit_button_selector)

        self.custom_fill(self.field_has_name_selector, new_data.name)
        self.custom_click(self.type_name_dropdown_selector)
        self.custom_click(self.type_name_option_selector, has_text=new_data.type)
        if new_data.show:
            self.custom_click(self.field_has_visible_selector)
        self.custom_click(self.save_button_selector)
        self.wait_spinner_loader()

    def delete_custom_field(self, name: str) -> None:
        """Two clicks on ButtonDelete: the menu item, then the confirmation in the modal."""
        field = self.page.locator(self.custom_fields_list_selector, has_text=name)
        field.locator(self.dropdown_dots_selector).click()
        self.custom_click(self.delete_button_selector)
        self.custom_click(self.delete_button_selector)
        self.wait_spinner_loader()

    def search_custom_field(self, name: str) -> None:
        self.custom_fill(self.search_input_selector, name)
        self.wait_spinner_loader()

    def set_view(self, view: int) -> None:
        self.custom_click(self.pagination_amount_selector)
        self.custom_click(f'[data-dropdown-id="{view}"]')
        self.wait_spinner_loader()

    def verify_custom_fields_list(self, fields: list[CustomField]) -> None:
        """Rows are found by name, so this does not depend on table order.

        Visibility is read from the dash placeholder the table renders for a hidden field:
        there is no checkbox, so the absence of that placeholder means the field is shown.
        """
        for field in fields:
            row = self.page.locator(self.custom_fields_list_selector, has_text=field.name)
            field_type = (row.locator(self.field_type_label_selector).text_content() or "").strip()
            field_show = row.locator(self.not_show_in_conversations_selector).count() == 0

            assert field_type == field.type, f"{field.name}: expected type {field.type}, got {field_type}"
            assert field_show == field.show, f"{field.name}: expected show={field.show}, got {field_show}"
            expect(row.locator(self.field_name_label_selector)).to_have_text(field.name)

    def verify_help_text(self, message: str) -> None:
        """Inline validation under the name input, e.g. "Name already exists"."""
        expect(self.page.locator(self.help_text_selector)).to_have_text(message)

    def verify_custom_fields_counter(self, counter: str) -> None:
        """Expected strings carry odd spacing and a zero-width space because the app renders
        them that way; normalising would weaken the check."""
        expect(self.page.locator(self.toolbox_center_selector).first).to_contain_text(counter)
