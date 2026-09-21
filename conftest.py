"""Root pytest configuration.

pytest imports conftest.py by itself - it is never imported by hand and never appears in an
import statement. Everything defined here is visible to every test below it in the tree.
"""

from __future__ import annotations

import logging

import pytest

from src.config import settings

pytest_plugins = [
    "fixtures.accounts",
    "fixtures.pages",
    "fixtures.data",
]


def pytest_configure(config: pytest.Config) -> None:
    """httpx logs every request at INFO and drowns the live log in noise."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Browser context options.

    Taking the same name as an argument gets pytest-playwright's original value, which is then
    extended rather than replaced - the standard way to customise a plugin's fixture.

    The viewport matters: any narrower and the app collapses into a layout with different
    selectors.
    """
    args = {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 750},
        "permissions": ["microphone"],
    }
    if settings.basic_username and settings.basic_password:
        args["http_credentials"] = {
            "username": settings.basic_username,
            "password": settings.basic_password,
            "send": "always",
        }
    return args


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    """--disable-dev-shm-usage stops Chromium running out of shared memory in containers,
    which otherwise shows up as random crashes in CI."""
    return {**browser_type_launch_args, "args": ["--disable-dev-shm-usage"]}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run adapted UI scenarios against your disposable test environment",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.parent.name != "tests":
            continue
        item.add_marker(pytest.mark.e2e)
        if not config.getoption("--run-e2e"):
            item.add_marker(pytest.mark.skip(reason="Requires adapted test app; use --run-e2e explicitly"))
    if config.getoption("--run-e2e") and not settings.environment_url:
        raise pytest.UsageError("Set ENVIRONMENT_URL for your disposable test app before --run-e2e")
