"""Playwright wrappers shared by every page object."""

from __future__ import annotations

import contextlib
import logging
import re
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Literal

from playwright.sync_api import BrowserContext, Locator, Page

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60_000

Modifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]

try:
    import allure

    _ALLURE = True
except ImportError:
    _ALLURE = False


class CustomCommands:
    def __init__(self, page: Page, context: BrowserContext) -> None:
        self.page = page
        self.context = context
        self.page.on("dialog", self._accept_dialog)

    @staticmethod
    def _accept_dialog(dialog: Any) -> None:
        with contextlib.suppress(Exception):
            dialog.accept()

    def custom_selector(
        self,
        selector: str | Locator,
        *,
        nth: int = 0,
        selector_type: Literal["byLocator", "byText"] | None = None,
        has_text: str | re.Pattern[str] | None = None,
        has_not_text: str | re.Pattern[str] | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        """Accept either a CSS string or a ready Locator, so page objects can pass both."""
        if isinstance(selector, Locator):
            return selector

        if selector_type == "byText":
            return self.page.get_by_text(selector)

        return self.page.locator(
            selector,
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        ).nth(nth)

    def custom_click(
        self,
        selector: str | Locator,
        *,
        nth: int = 0,
        selector_type: Literal["byLocator", "byText"] | None = None,
        has_text: str | re.Pattern[str] | None = None,
        has: Locator | None = None,
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
        force: bool = False,
        modifiers: Sequence[Modifier] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        hidden: bool = False,
    ) -> None:
        """Click an element, logging its text.

        `hidden=True` waits for the element to disappear afterwards - use it on anything that
        closes a modal, or the next command races the closing animation.
        """
        locator = self.custom_selector(selector, nth=nth, selector_type=selector_type, has_text=has_text, has=has)
        locator.wait_for(state="visible", timeout=timeout)
        log.info('Click: "%s"', (locator.text_content() or "").strip())

        locator.click(
            button=button,
            click_count=click_count,
            force=force,
            modifiers=list(modifiers) if modifiers else None,
        )

        if hidden:
            locator.wait_for(state="hidden", timeout=timeout)

    def custom_hover(
        self,
        selector: str | Locator,
        *,
        nth: int = 0,
        has_text: str | re.Pattern[str] | None = None,
        force: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Hover. Several row actions only render once the row is hovered."""
        locator = self.custom_selector(selector, nth=nth, has_text=has_text)
        locator.wait_for(state="visible", timeout=timeout)
        log.info('Hover: "%s"', (locator.text_content() or "").strip())
        locator.hover(force=force, timeout=timeout)

    def custom_fill(
        self,
        selector: str | Locator,
        value: str,
        *,
        nth: int = 0,
        has_text: str | re.Pattern[str] | None = None,
        logs: bool = True,
        value_clear: bool = True,
        enter: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Type into a field.

        `logs=False` masks the value - always pass it for passwords.
        `value_clear=False` appends to what is already there instead of replacing it.
        """
        locator = self.custom_selector(selector, nth=nth, has_text=has_text)
        locator.wait_for(state="visible", timeout=timeout)
        log.info(
            'Fill "%s": %s',
            (locator.get_attribute("placeholder") or "").strip(),
            value if logs else "*" * 9,
        )

        locator.fill(value if value_clear else f"{locator.input_value()} {value}")

        if enter:
            locator.press("Enter")

    def is_element_present(self, selector: str, timeout: float = 5000) -> bool:
        """Presence check that returns False instead of raising."""
        try:
            self.page.wait_for_selector(selector, state="attached", timeout=timeout)
            return True
        except Exception:
            return False

    def click_if_element_present(self, selector: str, **click_options: Any) -> None:
        """Click only if present - for banners and modals that appear unpredictably."""
        if self.is_element_present(selector):
            self.custom_click(selector, **click_options)
        else:
            log.info("Not present, skipping click: %s", selector)

    def click_if_iframe_present(self, iframe: str, selector: str, **click_options: Any) -> None:
        """Same, for an element inside an iframe."""
        if not self.is_element_present(iframe):
            log.info("Not present, skipping click: %s", iframe)
            return

        target = self.page.locator(iframe).content_frame.locator(selector)
        self.custom_hover(target)
        self.custom_click(target, **click_options)

    @contextmanager
    def wrapped_test_step(self, step_name: str) -> Iterator[None]:
        """Group actions into a named, timed step, and into an Allure step when installed."""
        started = time.monotonic()
        log.info("[STEP] %s", step_name)
        if _ALLURE:
            with allure.step(step_name):
                yield
        else:
            yield
        log.info("[STEP] %s: %.1fs", step_name, time.monotonic() - started)

    def clear_cache_cookies(self) -> None:
        """Sign the browser out completely, before re-authenticating as another role."""
        self.page.evaluate("() => localStorage.clear()")
        self.context.clear_cookies()
