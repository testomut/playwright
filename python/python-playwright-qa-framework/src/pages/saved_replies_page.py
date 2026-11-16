"""Saved replies page object.

A saved reply is a reusable message template: text plus emoji, attachments, merge fields and
shortened links.
"""

from __future__ import annotations

from playwright.sync_api import BrowserContext, Page, expect

from src.pages.settings_page import SettingsPage
from src.types.models import Visibility


class SavedRepliesPage(SettingsPage):
    create_reply_button_selector = '[aria-label="ButtonNewReply"]'
    title_input_selector = 'input[placeholder="Title"]'
    message_field_selector = '[aria-label="TextInput_MessageField"]'
    emoji_picker_trigger_selector = '[aria-label="IconButtonEmojiPicker_Default"]'
    merge_fields_trigger_selector = (
        '[aria-label="DropdownMergeFieldsIconAction_Trigger"] [aria-label="IconButtonTrigger_Default"]'
    )
    shorten_url_trigger_selector = '[aria-label="IconButtonShortenUrl_Default"]'
    visibility_trigger_selector = '[aria-label="ButtonMyselfOnly"], [aria-label="ButtonAllMembers"]'
    cancel_button_selector = '[aria-label="ButtonCancel"]'
    create_button_selector = '[aria-label="ButtonCreate"]'
    save_changes_button_selector = '[aria-label="ButtonSaveChanges"]'
    saved_reply_row_title_selector = '[aria-label="TypographyTitle"]'
    saved_reply_shared_icon_selector = '[aria-label="Tooltip"]'

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def open_new_reply_form(self) -> None:
        self.custom_click(self.create_reply_button_selector)
        expect(self.page.locator(self.title_input_selector)).to_be_visible()

    def fill_saved_reply_form(
        self,
        title: str,
        message: str,
        *,
        emoji: str | None = None,
        file: str | None = None,
        merge_field: str | None = None,
        url: str | None = None,
    ) -> None:
        """Everything past `message` is optional, so a test adds only the content it cares about."""
        self.custom_fill(self.title_input_selector, title)
        self.custom_fill(self.message_field_selector, message)

        if emoji:
            self.custom_click(self.emoji_picker_trigger_selector)
            self.custom_click(f'[aria-label="{emoji}"]')
        if file:
            self.upload_and_verify_files([file])
        if merge_field:
            self.custom_click(self.merge_fields_trigger_selector)
            self.custom_click(self.merge_field_examplecrm_button_selector)
            self.custom_click(f'[aria-label="{merge_field.replace(" ", "")}"]')
        if url:
            self.custom_click(self.shorten_url_trigger_selector)
            self.custom_fill(self.shorten_url_input_selector, url)
            self.custom_click(self.add_url_button_selector)

    def verify_saved_reply_visibility(self, visibility: Visibility) -> None:
        actual = (self.page.locator(self.visibility_trigger_selector).text_content() or "").strip()
        assert actual == visibility, f"Expected visibility {visibility}, got {actual}"

    def set_saved_reply_visibility(self, visibility: Visibility) -> None:
        """The trigger is one button whose aria-label changes with its state, which is why the
        selector matches both spellings."""
        self.custom_click(self.visibility_trigger_selector)
        self.custom_click(self.dropdown_list_item_selector, has_text=visibility)
        self.verify_saved_reply_visibility(visibility)

    def create_saved_reply(self, title: str) -> None:
        """Submit and assert the post-create state.

        All three checks have regressed before: the toast, the shared icon on the new row, and
        Cancel/Save being disabled, which is how the form signals it has no unsaved changes.
        """
        self.custom_click(self.create_button_selector)
        self.verify_toast_item("Saved reply created")

        row = self.page.locator(self.saved_reply_row_title_selector, has_text=title).locator("..")
        expect(row.locator(self.saved_reply_shared_icon_selector)).to_have_count(2)
        expect(self.page.locator(self.cancel_button_selector)).to_be_disabled()
        expect(self.page.locator(self.save_changes_button_selector)).to_be_disabled()
