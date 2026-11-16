"""Account and API-client fixtures.

Fixture scope is the thing to understand here:

    scope="session"  built once per pytest process and shared by every test in it. Under
                     `pytest -n`, each worker is its own process, so each gets its own.
    scope="function" (the default) rebuilt for every test.

The API client is session-scoped so its connection pool is reused. Anything touching a browser
is function-scoped, because a test must never inherit another test's page state.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest

from src.config import ACCOUNTS_DIR, settings
from src.constants.functions import load_user_accounts
from src.types.models import RegistrationData
from src.utils.api_requests import ApiRequests


def worker_index() -> int:
    """pytest-xdist sets PYTEST_XDIST_WORKER to gw0, gw1, ...; it is absent single-process."""
    worker = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    return int(worker.removeprefix("gw")) if worker.startswith("gw") else 0


def _pinned_account() -> RegistrationData | None:
    """Load the account named by ACCOUNT, if that variable is set.

    ACCOUNT=account3 forces every test onto one account regardless of worker, which is how a
    failure is reproduced locally. Run single-process when using it.
    """
    if not settings.account:
        return None
    raw = json.loads((ACCOUNTS_DIR / f"{settings.account}.json").read_text(encoding="utf-8"))
    member = raw.get("member") or {}
    member.setdefault("first_name", member.pop("firstName", ""))
    member.setdefault("last_name", member.pop("lastName", ""))
    return RegistrationData.model_validate(raw)


@pytest.fixture(scope="session")
def user_accounts() -> list[RegistrationData | None]:
    return load_user_accounts()


@pytest.fixture(scope="session")
def token_file() -> str:
    """Resolved to a path by ApiRequests: user0.json means variables/accounts/account0.json."""
    if settings.account:
        return f"user-{settings.account}.json"
    return f"user{worker_index()}.json"


@pytest.fixture
def user_details(user_accounts: list[RegistrationData | None]) -> RegistrationData:
    """The account this test runs against.

    A skip rather than an error on a missing account: `pytest -n 8` with three accounts
    provisioned should report five skips with a clear reason, not five crashes.
    """
    index = worker_index()
    account = _pinned_account() or (user_accounts[index] if index < len(user_accounts) else None)
    if account is None:
        pytest.skip(f"variables/accounts/account{worker_index()}.json is not provisioned")
    return account


@pytest.fixture(scope="session")
def api_request() -> Iterator[ApiRequests]:
    """A fixture that yields is a setup/teardown pair: the code before the yield runs first,
    the yielded value goes to the test, and the rest runs when the scope ends.

    Note that if the setup half raises, the teardown half never runs - execution never reached
    the yield. Anything that must be cleaned up has to be created before the risky code.
    """
    client = ApiRequests()
    yield client
    client.close()


@pytest.fixture
def authorized_token(api_request: ApiRequests, user_details: RegistrationData, token_file: str) -> str:
    """Sign in over the API and cache the token on the account object.

    Assigning to user_details.token matters: the other fixtures and the tests read it from
    there rather than taking it as an argument.
    """
    user_details.token = api_request.login(user_details.email, user_details.password, token_file)
    return user_details.token


@pytest.fixture(scope="session")
def old_account_token(api_request: ApiRequests) -> str:
    """The shared account on the other end of every test conversation - one login per worker."""
    return api_request.login(settings.old_account_email, settings.old_account_pass, "old.json")
