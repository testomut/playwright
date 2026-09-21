"""Phone formatting and account loading.

The app renders the same number three different ways depending on where it appears, and
assertions have to match what is on screen - hence three formatters.
"""

from __future__ import annotations

import json
import logging
import re

from src.config import ACCOUNTS_DIR, settings
from src.types.models import ProtectedBlock, ProtectedNumber, RegistrationData

log = logging.getLogger(__name__)

DEFAULT_PROTECTED_INBOXES = ["Main inbox", "Demo Inbox"]


def only_digits(phone: str | int | None) -> str:
    return re.sub(r"\D", "", str(phone)) if phone is not None else ""


def format_phone_number(phone: str | int | None) -> str:
    """Conversation-list rendering: "+1 202 555 0101"."""
    cleaned = only_digits(phone)
    if not cleaned:
        return ""
    if len(cleaned) == 10:
        return f"+1 {cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
    if len(cleaned) == 11 and cleaned.startswith("1"):
        return f"+{cleaned[0]} {cleaned[1:4]} {cleaned[4:7]} {cleaned[7:]}"
    return f"+{cleaned}"


def format_phone_number_to_formatted_number(phone: str | int | None) -> str:
    """Table-cell rendering: "(202) 555-0101". This is also what the API returns."""
    cleaned = only_digits(phone)
    if not cleaned:
        return ""
    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    if len(cleaned) == 11 and cleaned.startswith("1"):
        return f"({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
    return str(phone)


def format_phone_number_to_only_numbers(phone: str | int | None) -> str:
    """Search-input rendering: digits only."""
    return only_digits(phone)


def load_user_accounts() -> list[RegistrationData | None]:
    """Load one account per worker slot.

    Returns a fixed-length list indexed by worker number, with None where no file is
    provisioned - fixtures/accounts.py turns that into a skip with a clear reason. A file that
    exists but is malformed raises instead, because a silent skip would hide a real problem.

    Required fields are checked by hand before pydantic sees them so the error names the file
    rather than just the field. Files predating the protected block get a minimal one rebuilt,
    so cleanup still knows which number it must not delete.
    """
    accounts: list[RegistrationData | None] = [None] * settings.workers
    if not ACCOUNTS_DIR.exists():
        return accounts

    for index in range(settings.workers):
        account_file = ACCOUNTS_DIR / f"account{index}.json"
        if not account_file.exists():
            continue

        raw = json.loads(account_file.read_text(encoding="utf-8"))
        if not raw:
            log.info("account%s.json is an empty placeholder, skipping", index)
            continue

        for required in ("email", "firstName", "lastName", "password", "organizationId"):
            if not raw.get(required):
                raise ValueError(f"account{index}.json is missing {required}")
        if not (raw.get("member") or {}).get("email"):
            raise ValueError(f"account{index}.json is missing member data")

        if not (raw.get("protected") or {}).get("numbers"):
            raw["protected"] = ProtectedBlock(
                numbers=[ProtectedNumber(role="business", type="local", formatted=raw.get("businessNumber"))],
                inboxes=list(DEFAULT_PROTECTED_INBOXES),
            ).model_dump()

        member = raw["member"]
        member.setdefault("first_name", member.pop("firstName", ""))
        member.setdefault("last_name", member.pop("lastName", ""))

        accounts[index] = RegistrationData.model_validate(raw)

    return accounts
