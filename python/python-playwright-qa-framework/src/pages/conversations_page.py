"""Conversations page object.

The conversation list is both virtualised and infinitely scrolled, so finding a conversation
is a scroll loop rather than a locator lookup - see find_conversation_card.
"""

from __future__ import annotations

import time

from playwright.sync_api import BrowserContext, Locator, Page

from src.constants.functions import format_phone_number
from src.pages.base_page import BasePage


class ConversationsPage(BasePage):
    conversation_layout_header_title_selector = '[aria-label="ActiveConversationNameContainerHeader"]'
    conversations_list_selector = '[aria-label="ConversationCard"]'
    conversations_name_list_selector = '[aria-label="ConversationCardName"]'
    full_inboxes_list_selector = '[aria-label="TypographyName"]'
    message_input_selector = '[aria-label="TextInput_MessageField"]'
    note_input_selector = '[placeholder="Type @ to mention..."]'
    remove_attachment_button_selector = '[aria-label="RemovableAttachment_RemoveButton"]'
    attachment_card_selector = '[aria-label="MessageField"] [aria-label="AttachmentCard"]'

    def __init__(self, page: Page, context: BrowserContext) -> None:
        super().__init__(page, context)

    def find_conversation_card(
        self, conversation: str, phone: bool = False, timeout: float = 120_000
    ) -> Locator | None:
        """Scroll the conversation list until the wanted card appears.

        A plain locator will not do: the list renders a window of cards and loads more only as
        you scroll, so a conversation further down is simply not in the DOM yet.

        Two stop conditions: the rendered count stopped growing (end of list reached, so scroll
        back to the top and sweep once more), or nothing renders at all (the list is empty).
        """
        search = format_phone_number(conversation) if phone else conversation
        card = self.page.locator(self.conversations_name_list_selector, has_text=search).first
        cards = self.page.locator(self.conversations_list_selector)

        deadline = time.monotonic() + timeout / 1000
        last_rendered = -1
        stable_rounds = 0

        while time.monotonic() < deadline:
            if card.count() > 0:
                return card

            rendered = cards.count()
            if rendered:
                stable_rounds = stable_rounds + 1 if rendered == last_rendered else 0
                if stable_rounds >= 3:
                    cards.nth(0).scroll_into_view_if_needed()
                    stable_rounds = 0
                else:
                    cards.nth(rendered - 1).scroll_into_view_if_needed()

            last_rendered = rendered
            self.page.wait_for_timeout(500)

        return None

    def select_conversation(self, conversation: str, phone: bool = False, timeout: float = 120_000) -> None:
        search = format_phone_number(conversation) if phone else conversation
        card = self.find_conversation_card(conversation, phone, timeout)
        if card is None:
            raise AssertionError(f'Conversation "{search}" never appeared in the list')

        card.click()
        self.wait_spinner_loader()

    def select_inbox(self, inbox: str) -> None:
        """Switch the left sidebar to another inbox.

        The spinner wait is conditional: clicking the already active inbox reloads nothing, so
        waiting for a spinner that never appears would hang. nth=2 because this view stacks
        three spinners and only the third one tracks the inbox load.
        """
        inbox_locator = self.page.locator(self.full_inboxes_list_selector).get_by_text(inbox, exact=True)
        header = self.page.locator(self.conversation_layout_header_title_selector).first
        selected = header.text_content() if header.count() else None

        self.custom_click(inbox_locator)
        if selected != inbox:
            self.wait_spinner_loader(2)

    def clear_input_message(self) -> None:
        """Empty the composer.

        The app persists drafts per conversation, so text left by an earlier test would show up
        in this one. `.or_()` because the field is either a message or a note, never both.
        """
        message_input = self.page.locator(self.message_input_selector)
        note_input = self.page.locator(self.note_input_selector)
        self.custom_fill(message_input.or_(note_input), "")
        self.remove_all_attachments()

    def remove_all_attachments(self) -> None:
        """Always remove index 0: the list re-renders after each removal, staling any locator."""
        for _ in range(self.page.locator(self.remove_attachment_button_selector).count()):
            self.custom_hover(self.attachment_card_selector, nth=0)
            self.custom_click(self.remove_attachment_button_selector, nth=0, force=True)
