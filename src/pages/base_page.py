"""Base class for every page object.

CustomCommands -> BasePage -> SettingsPage -> TagsPage / CustomFieldsPage / SavedRepliesPage
                           -> ContactsPage / ConversationsPage
"""

from __future__ import annotations

import contextlib
import logging

from playwright.sync_api import BrowserContext, Page, expect

from src.config import FILES_DIR, settings
from src.utils.custom_commands import DEFAULT_TIMEOUT, CustomCommands

log = logging.getLogger(__name__)

MEDIA_PATHS: dict[str, str] = {
    "audio": "test_audio.mp3",
    "img": "test_image.png",
    "video": "test_video.mp4",
    "doc": "test_doc_file.doc",
    "pdf": "test_pdf_file.pdf",
    "csv": "test_csv_file.csv",
}


class BasePage(CustomCommands):
    user_icon_selector = '[aria-label="DropdownMainDropdown"]'
    settings_selector = '[aria-label="TypographySettings"]'
    open_contacts_page_selector = '[aria-label="NavLink_Contacts"]'

    banner_accept_selector = '[data-tid="banner-accept"]'
    broadcast_handle_replies_close_selector = '[aria-label="IconButtonCloseBroadcastsPopup"]'
    banner_recommended_selector = '[data-testid="banner-survey-close-button"]'
    recommendation_banner_iframe_selector = "iframe.survey-banner-enter-done"
    chat_bot_iframe_selector = 'iframe[name="intercom-notification-stack-frame"]'
    close_chat_bot_selector = '[data-testid="notification-close-desktop"]'
    switch_v2_button_selector = ".switchDesignV2"

    application_loader_selector = ".app-loader"
    spinner_loader_selector = '[class = "spinner"] .MuiCircularProgress-circle'
    loader_page_selector = '[class="page is-loading"]'
    toast_item_selector = '[aria-label="ToastItem"]'

    edit_button_selector = '[aria-label="ButtonEdit"]'
    delete_button_selector = '[aria-label="ButtonDelete"]'
    dropdown_actions_selector = '[aria-label="DropdownActions"]'
    dropdown_list_item_selector = '[aria-label="DropdownList_Item"]'
    next_page_button_selector = '[aria-label="IconButtonPaginationNext"]'
    pagination_amount_selector = '[aria-label="DropdownPaginationSelect_Trigger"]'
    records_list_selector = '[aria-label="TableBody"] [data-index]'
    all_table_items_list_selector = '[aria-label="TableBody"]'
    contact_row_cell_number_selector = '[aria-label="ContactRowCellNumber"]'
    plan_credits_exceeded_selector = '[aria-label="TypographyPlanCreditsExceeded"]'
    close_alert_button_selector = '[aria-label="IconButtonAlertClose"]'

    merge_field_examplecrm_button_selector = '[aria-label="MergeFieldExampleCRM"]'
    shorten_url_input_selector = '[placeholder="Enter your URL"]'
    add_url_button_selector = '[aria-label="ButtonAddUrl"]'
    added_media_files_list_selector = '[aria-label="MessageField"] [aria-label="AttachmentCard"]'
    attachment_loader_selector = '[aria-label="AttachmentLoader"]'
    upload_files_selector = '[aria-label="UploadFile_MessageField"] input[type="file"]'
    add_media_selector = '[aria-label="IconButtonMediaActionAddMedia_Default"]'

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def wait_spinner_loader(self, nth: int = 0) -> None:
        """Wait out a section spinner.

        The spinner appears a beat after the click, so waiting only for "detached" would return
        before it had rendered. Waiting for "attached" first fixes that, and tolerates the case
        where no spinner shows up at all.
        """
        spinner = self.page.locator(self.spinner_loader_selector).nth(nth)
        with contextlib.suppress(Exception):
            spinner.wait_for(state="attached", timeout=2000)
        spinner.wait_for(state="detached", timeout=DEFAULT_TIMEOUT)

    def wait_loader_old_design(self) -> None:
        """The legacy pages - Tags is one - use a different loader entirely."""
        loader = self.page.locator(self.loader_page_selector)
        with contextlib.suppress(Exception):
            loader.wait_for(state="attached", timeout=2000)
        loader.wait_for(state="detached", timeout=DEFAULT_TIMEOUT)

    def wait_application_loader(self, timeout: float = 30_000) -> None:
        """Wait for the SPA to finish booting."""
        self.page.locator(self.application_loader_selector).wait_for(state="detached", timeout=timeout)

    def wait_attachment_ready(self) -> None:
        """An upload is done when the card is visible and no loader remains inside it."""
        cards = self.page.locator(self.added_media_files_list_selector)
        expect(cards.last).to_be_visible(timeout=DEFAULT_TIMEOUT)
        expect(cards.locator(self.attachment_loader_selector)).to_have_count(0, timeout=DEFAULT_TIMEOUT)

    def reload(self) -> None:
        self.page.reload()
        self.wait_application_loader()
        self.wait_spinner_loader()

    def accept_cookie_banner(self) -> None:
        """Dismiss the cookie banner, deleting the Intercom iframe that overlaps it.

        Removing the iframe outright beats finding and clicking its close button, and nothing
        under test depends on Intercom.
        """
        self.page.evaluate(
            "(sel) => { const iframe = document.querySelector(sel); if (iframe) iframe.remove(); }",
            self.chat_bot_iframe_selector,
        )
        self.click_if_element_present(self.banner_accept_selector, hidden=True, force=True)

    def dismiss_popups(self) -> None:
        """Clear everything that can sit over a button before the test starts clicking."""
        self.click_if_iframe_present(self.chat_bot_iframe_selector, self.close_chat_bot_selector, hidden=True)
        self.accept_cookie_banner()
        self.click_if_element_present(self.broadcast_handle_replies_close_selector, hidden=True)
        self.click_if_iframe_present(
            self.recommendation_banner_iframe_selector,
            self.banner_recommended_selector,
            hidden=True,
        )

    def wait_oauth_response_load(self) -> None:
        """Settle the page after a form login."""
        self.wait_application_loader()
        self.wait_spinner_loader()
        self.click_if_element_present(self.switch_v2_button_selector)

    def oauth_with_token(self, token: str, page: str = "conversations") -> None:
        """Sign in by writing the JWT into localStorage instead of filling the login form.

        The retry loop is not paranoia: the SPA sometimes boots, reads an empty localStorage and
        redirects to /auth/login before the write lands, wiping the token on the way.
        """
        for attempt in range(1, 4):
            self.page.goto(f"{settings.environment_url}/{page}")
            self.page.evaluate("(value) => localStorage.setItem('token', value)", token)
            self.page.goto(f"{settings.environment_url}/{page}")
            self.wait_application_loader()

            if "/auth/login" not in self.page.url:
                break
            log.info("Token did not survive the sign in page, attempt %s/3", attempt)
        else:
            raise RuntimeError("Application stayed on the sign in page - the token was dropped")

        self.wait_spinner_loader()
        self.dismiss_popups()

    def verify_toast_item(self, contains_text: str | None = None, nth: int = 0) -> None:
        """Assert a toast appears, then wait it out - a lingering toast eats the next click."""
        toast = self.page.locator(self.toast_item_selector).nth(nth)
        toast.wait_for(state="visible", timeout=DEFAULT_TIMEOUT)
        if contains_text:
            expect(toast).to_contain_text(contains_text)
        toast.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT)

    def close_plan_credits_exceeded(self) -> None:
        """Dismiss the "out of credits" banner a long-lived account eventually shows."""
        if self.page.locator(self.plan_credits_exceeded_selector).is_visible():
            self.custom_click(self.close_alert_button_selector)

    def upload_and_verify_files(self, files: list[str], verify: bool = True) -> None:
        """Attach files by driving the file input directly, so no OS dialog opens."""
        self.custom_click(self.add_media_selector)
        self.page.locator(self.upload_files_selector).set_input_files(
            [str(FILES_DIR / MEDIA_PATHS[name]) for name in files]
        )
        self.wait_spinner_loader()
        self.page.keyboard.press("Escape")
        if verify:
            self.wait_attachment_ready()
