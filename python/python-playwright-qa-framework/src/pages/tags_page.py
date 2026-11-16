"""Tags page object.

The shape every page object here follows: selectors, then expected message constants, then
actions, then verify_* assertions. Tests only call these methods and never touch page.locator,
which is what keeps a UI change contained to one file.
"""

from __future__ import annotations

import logging
from typing import Literal

from playwright.sync_api import BrowserContext, Page

from src.constants.functions import format_phone_number
from src.pages.settings_page import SettingsPage
from src.types.models import TagAlertType, TagData
from src.utils.api_requests import ApiRequests

log = logging.getLogger(__name__)

SortType = Literal["Name", "Contacts"]
ContactSortType = Literal["Name", "Phone", "Email", "Created At"]
SortDirection = Literal["to high", "to low"]


class TagsPage(SettingsPage):
    """Rows are addressed through their cells: `td` index 2 holds the contact counter, which is
    both the value the assertions read and the cell that opens the tag's contact list."""

    create_tag_button_selector = '[aria-label="ButtonNewTag"]'
    create_tag_modal_cancel_button_selector = '[aria-label="ButtonCancel"]'
    create_tag_modal_input_selector = '[placeholder="Enter tag name"]'
    create_tag_modal_save_button_selector = '[aria-label="ButtonCreate"]'
    tags_update_button_selector = '[aria-label="ButtonUpdate"]'
    tag_item_selector = '[aria-label="TagsRow"]'
    tag_name_selector = '[aria-label="TypographyTagsName"]'
    three_dots_selector = '[aria-label="DropdownActions"]'
    tags_edit_button_selector = '[aria-label="ButtonRename"]'
    tags_delete_button_selector = '[aria-label="ButtonDelete"]'
    submit_delete_button_selector = '[aria-label="Modal_DeleteTags"] [aria-label="ButtonDelete"]'
    search_input_selector = '[placeholder="Search..."]'
    contacts_tag_selector = "td"
    sorting_button_selector = "th"
    checkbox_selector = '[aria-label="Checkbox"]'
    tags_amount_selector = '[aria-label="PaginationSelect_Value"]'
    tags_scroll_container_selector = '[aria-label="Scrollbar_View"]:has([aria-label="TableBody"])'
    warning_text_selector = '[aria-label="TypographyWarning"]'
    error_text_selector = '[aria-label="TypographyError"]'
    tooltip_selector = '[aria-label="Tooltip"]'
    tooltip_value_selector = '[aria-label="TypographyFormattedValue"]'

    error_text_tag_modal_created = "The tag name has already been taken."
    error_text_tag_modal_long_name = "Tag name must not be longer than 50 characters."

    def __init__(self, page: Page, context: BrowserContext, api_request: ApiRequests | None = None) -> None:
        super().__init__(page, context)
        self.api_request = api_request or ApiRequests()

    def create_tag(self, tag: str) -> None:
        self.custom_click(self.create_tag_button_selector)
        self.custom_fill(self.create_tag_modal_input_selector, tag)
        self.custom_click(self.create_tag_modal_save_button_selector)
        self.verify_toast_item("Tag created")

    def create_tag_with_error(self, tag: str, create: bool = True) -> None:
        """create=False stops before submitting, for the inline warning shown while typing."""
        self.custom_click(self.create_tag_button_selector)
        self.custom_fill(self.create_tag_modal_input_selector, tag)
        if create:
            self.click_save_button()

    def create_a_lot_tags(self, count: int, tag_name: str, token: str) -> None:
        """Seed N tags over the API, named Tag0, Tag1, ... - the tests assert on those names."""
        for index in range(count):
            self.api_request.tags(token, f"{tag_name}{index}")

    def click_save_button(self) -> None:
        self.custom_click(self.create_tag_modal_save_button_selector)

    def click_update_button(self) -> None:
        self.custom_click(self.tags_update_button_selector)

    def click_cancel_button(self) -> None:
        self.custom_click(self.create_tag_modal_cancel_button_selector)

    def action_on_3_dots(self, tag: str, action: Literal["Edit", "Delete"], tag_name: str | None = None) -> None:
        """Open a row's three-dots menu and pick an action.

        Delete clicks the same selector twice on purpose: the menu item and the confirmation in
        the modal it opens both carry aria-label="ButtonDelete".
        """
        tag_item = self.page.locator(self.tag_item_selector).filter(has_text=tag)
        if action == "Edit":
            tag_item.locator(self.three_dots_selector).click()
            self.custom_click(self.tags_edit_button_selector)
            if tag_name:
                self.custom_fill(self.create_tag_modal_input_selector, tag_name)
                self.custom_click(self.tags_update_button_selector)
                self.verify_toast_item("Tag name updated")
        elif action == "Delete":
            tag_item.locator(self.three_dots_selector).click()
            self.custom_click(self.tags_delete_button_selector)
            self.custom_click(self.tags_delete_button_selector)
            self.verify_toast_item("Tag deleted")

    def rename_tag(self, tag_name: str, new_tag_name: str, update: bool = True) -> None:
        """update=False leaves the modal open so a test can read the warning."""
        tag_item = self.page.locator(self.tag_item_selector).filter(has_text=tag_name)
        tag_item.locator(self.three_dots_selector).click()
        self.custom_click(self.tags_edit_button_selector)
        self.custom_fill(self.create_tag_modal_input_selector, new_tag_name)
        if update:
            self.custom_click(self.tags_update_button_selector)
            self.verify_toast_item("Tag name updated")

    def use_search(self, tag_name: str) -> None:
        self.custom_fill(self.search_input_selector, tag_name)
        self.wait_spinner_loader()

    def select_tag(self, tag_name: str) -> None:
        """Open a tag's contact list by clicking its contact-count cell."""
        tag_item = self.page.locator(self.tag_item_selector).filter(has_text=tag_name)
        tag_item.locator(self.contacts_tag_selector).nth(2).click()
        self.wait_spinner_loader()

    def delete_some_tags_by_bulk(self, tag_names: list[str]) -> None:
        for tag_name in tag_names:
            tag_item = self.page.locator(self.tag_item_selector).filter(has_text=tag_name)
            tag_item.locator(self.checkbox_selector).click()
        self.custom_click(self.tags_delete_button_selector)
        self.custom_click(self.submit_delete_button_selector)
        self.verify_toast_item("Tags deleted")

    def set_pagination_tags(self, count: int) -> None:
        self.custom_click(self.pagination_amount_selector)
        self.custom_click(f'[data-dropdown-id="{count}"]')
        self.wait_spinner_loader()

    def click_next_page(self, page_clicks: int) -> None:
        """Page forward N times, waiting for the range counter to change after each click."""
        for _ in range(page_clicks):
            before = self.page.locator(self.tags_amount_selector).text_content()
            self.custom_click(self.page.locator(self.next_page_button_selector).nth(0))
            self.page.wait_for_function(
                "([sel, prev]) => document.querySelector(sel)?.textContent !== prev",
                arg=[self.tags_amount_selector, before],
            )

    def sort_tags(self, sort_type: SortType, count: int, expected_tags: list[TagData]) -> None:
        """Sort by a column and assert the order. Column 0 is the checkbox.

        The assertion is two-part because the backend does not order rows that have an equal
        contact count: the counts must match exactly, and within each count the names must
        match as a set. Comparing the list directly is flaky about one run in five.
        """
        column = 1 if sort_type == "Name" else 2
        self.custom_click(self.sorting_button_selector, nth=column)
        self.wait_spinner_loader()

        tags_count = self.page.locator(self.tag_item_selector).count()
        assert tags_count == count, f"Expected {count} tags, got {tags_count}"

        actual_tags = [
            TagData(
                tag_name=(row.locator(self.tag_name_selector).text_content() or "").strip(),
                contact=(row.locator(self.contacts_tag_selector).nth(2).text_content() or "").strip(),
            )
            for row in self.page.locator(self.tag_item_selector).all()[: len(expected_tags)]
        ]

        def contacts_of(tags: list[TagData]) -> list[str]:
            return [tag.contact for tag in tags]

        assert contacts_of(actual_tags) == contacts_of(expected_tags), (
            f"{sort_type} sort order mismatch. "
            f"Expected {contacts_of(expected_tags)}, got {contacts_of(actual_tags)}"
        )

        def names_by_contacts(tags: list[TagData]) -> list[tuple[str, list[str]]]:
            groups: dict[str, list[str]] = {}
            for tag in tags:
                groups.setdefault(tag.contact, []).append(tag.tag_name)
            return [(contact, sorted(names)) for contact, names in groups.items()]

        assert names_by_contacts(actual_tags) == names_by_contacts(expected_tags), (
            f"{sort_type} sort mismatch. Expected {expected_tags}, got {actual_tags}"
        )

    def sort_contacts(self, sort_type: ContactSortType, direction: SortDirection) -> None:
        """One click sorts descending, two ascending."""
        index = {"Name": 1, "Phone": 2, "Email": 3, "Created At": 4}[sort_type]
        self.custom_click(self.sorting_button_selector, nth=index)
        self.wait_spinner_loader()
        if direction == "to high":
            self.custom_click(self.sorting_button_selector, nth=index)
            self.wait_spinner_loader()

    def verify_tags_list(self, count: int, tags: list[TagData] | None = None) -> None:
        """Assert the row count, and optionally the contents of named rows.

        Counting is not locator.count(): the table is virtualised, so only visible rows are in
        the DOM. Scrolling to the bottom and reading data-index off the last row gives the
        position in the full list, so the last one is count - 1.
        """
        self.wait_spinner_loader()

        if count == 0:
            assert self.page.locator(self.tag_item_selector).count() == 0, "Tags list should be empty"
            return

        self.page.locator(self.tags_scroll_container_selector).evaluate(
            "(el) => { el.scrollTop = el.scrollHeight; }"
        )
        last_row = self.page.locator(self.tag_item_selector).last
        self.page.wait_for_function(
            "([sel, want]) => { const rows = document.querySelectorAll(sel);"
            " return rows.length && rows[rows.length - 1].getAttribute('data-index') === want; }",
            arg=[self.tag_item_selector, str(count - 1)],
        )

        for expected in tags or []:
            row = self.page.locator(self.tag_item_selector).filter(has_text=expected.tag_name)
            name = (row.locator(self.tag_name_selector).text_content() or "").strip()
            contact = (row.locator(self.contacts_tag_selector).nth(2).text_content() or "").strip()
            assert name == expected.tag_name, f"Expected tag {expected.tag_name}, got {name}"
            assert contact == expected.contact, f"Expected {expected.contact} contacts on {name}, got {contact}"
        assert last_row.get_attribute("data-index") == str(count - 1)

    def verify_tag_contacts_list(self, phone_numbers: list[str]) -> None:
        """Assert exactly these contacts are listed under the opened tag."""
        contacts_count = self.page.locator(self.tag_item_selector).count()
        assert contacts_count == len(phone_numbers), (
            f"Expected {len(phone_numbers)} contacts, got {contacts_count}"
        )
        for phone in phone_numbers:
            formatted = format_phone_number(phone)
            row = self.page.locator(self.tag_item_selector).filter(has_text=formatted)
            actual = (row.locator(self.contacts_tag_selector).nth(2).text_content() or "").strip()
            assert actual == formatted, f"Expected contact {formatted}, got {actual}"

    def verify_3_dots_contacts_name(self, contact_names: list[str]) -> None:
        """Assert a long name is truncated with an ellipsis rather than overflowing.

        Not visible in the DOM text, so it is measured in the browser: an element is truncated
        when scrollWidth exceeds clientWidth. The tooltip still carries the full name.
        """
        for name in contact_names:
            tooltip = self.page.locator(self.tooltip_selector).filter(has_text=name)
            value = tooltip.locator(self.tooltip_value_selector)
            full_text = (value.text_content() or "").strip()
            assert full_text == name, f"Tooltip should read {name}, got {full_text}"

            metrics = value.evaluate(
                "(el) => ({"
                " isTruncated: el.scrollWidth > el.clientWidth,"
                " hasEllipsis: window.getComputedStyle(el).textOverflow === 'ellipsis'"
                "})"
            )
            assert metrics["isTruncated"], f"{name} should be truncated"
            assert metrics["hasEllipsis"], f"{name} should have text-overflow: ellipsis"

    def verify_error(self, error_text: TagAlertType) -> None:
        """Assert a blocking validation error. The argument is a key, not the wording."""
        expected = {
            "exist": self.error_text_tag_modal_created,
            "long": self.error_text_tag_modal_long_name,
        }[error_text]
        actual = self.page.locator(self.error_text_selector).text_content()
        assert actual == expected, f"Expected error {expected}, got {actual}"

    def verify_warning(self, warning: str) -> None:
        """Substring match: the app appends a character counter to the message."""
        actual = self.page.locator(self.warning_text_selector).text_content() or ""
        assert warning in actual, f"Expected warning {warning}, got {actual}"

    def verify_from_tags_to_on_page(self, from_to: str) -> None:
        """Assert the pagination range, e.g. 31-40 out of the counter "31 - 40 of 120"."""
        raw = self.page.locator(self.tags_amount_selector).text_content() or ""
        actual = raw.split("of")[0].strip().replace(" ", "")
        assert actual == from_to, f"Expected range {from_to}, got {actual}"
