"""Environment configuration.

Every os.environ read lives here, so nothing else in the project touches the environment
directly.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
VARIABLES_DIR = ROOT_DIR / "variables"
ACCOUNTS_DIR = VARIABLES_DIR / "accounts"
TOKENS_DIR = VARIABLES_DIR / "tokens"
FILES_DIR = ROOT_DIR / "files"

load_dotenv(ROOT_DIR / ".env")


class Settings:
    """A typed, read-once view over the environment.

    Every attribute has a default, so importing this module never raises: a missing variable
    surfaces later as a clear failure in the call that needs it.
    """

    def __init__(self) -> None:
        self.environment_url: str = os.getenv("ENVIRONMENT_URL", "")
        self.env: str = os.getenv("ENV", "qa")
        self.api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.token_cookie: str = os.getenv("TOKEN", "token-qa")

        self.basic_username: str = os.getenv("BASIC_USERNAME", "")
        self.basic_password: str = os.getenv("BASIC_PASSWORD", "")

        self.old_account_email: str = os.getenv("OLD_ACCOUNT_EMAIL", "")
        self.old_account_pass: str = os.getenv("OLD_ACCOUNT_PASS", "")
        self.old_account_phone: str = os.getenv("OLD_ACCOUNT_PHONE", "")
        self.old_account_phone_short_code: str = os.getenv("OLD_ACCOUNT_PHONE_SHORT_CODE", "")

        self.workers: int = int(os.getenv("WORKERS", "5"))
        self.account: str | None = os.getenv("ACCOUNT") or None

    @property
    def api_url(self) -> str:
        """Explicit test API origin; no production-domain inference."""
        return self.api_base_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """lru_cache on a no-argument function is the idiomatic Python singleton."""
    return Settings()


settings = get_settings()
