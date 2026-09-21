"""Settings navigation, shared by every settings-area page object.

Each page is reached the same way: user menu -> Settings -> a link in the left column.
"""

from __future__ import annotations

from playwright.sync_api import BrowserContext, Page

from src.pages.base_page import BasePage


class SettingsPage(BasePage):
    custom_fields_selector = '[aria-label="NavLink_SettingsCustomFields"]'
    save_reply_selector = '[aria-label="NavLink_SettingsSavedReplies"]'
    tags_page_selector = '[href="/settings/tags"]'
    compliance_registration_popup_cancel_button_selector = ".button--cancel"

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def open_settings_page(self) -> None:
        """has_text disambiguates: the same aria-label is used by another item in that menu."""
        self.custom_click(self.user_icon_selector)
        self.custom_click(self.settings_selector, has_text="Settings")
        self.click_if_element_present(self.compliance_registration_popup_cancel_button_selector)
        self.wait_spinner_loader()

    def open_custom_fields_page(self) -> None:
        self.open_settings_page()
        self.custom_click(self.custom_fields_selector)
        self.page.locator(self.all_table_items_list_selector).first.wait_for(state="visible")

    def open_save_reply_page(self) -> None:
        self.open_settings_page()
        self.custom_click(self.save_reply_selector)
        self.wait_spinner_loader()

    def open_tags_page(self) -> None:
        """Tags is a legacy page, so it waits on the old loader rather than the spinner."""
        self.open_settings_page()
        self.custom_click(self.tags_page_selector)
        self.wait_loader_old_design()
