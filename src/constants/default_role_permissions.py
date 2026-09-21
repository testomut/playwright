"""Default permission sets per role.

The update-role endpoint replaces the whole permission object rather than patching it, so a
complete set has to be sent every time. clear_account also restores these before each test:
the accounts are permanent, and a test that narrowed a role would leave every later test
running with the wrong permissions.

They are functions, not module-level dicts, so each caller gets a fresh copy.
"""


def default_admin_permissions() -> dict:
    return {
        "broadcasts": True,
        "campaigns": True,
        "textBot": True,
        "triggers": True,
        "reportingAndAnalytics": True,
        "dataAndSecurity": True,
        "inbox": True,
        "members": True,
        "billing": True,
        "manualOptIn": True,
        "phoneChecker": True,
        "contactCreate": True,
        "transferConversation": False,
        "contactAccess": "can_access_all",
        "cannedMessage": True,
        "reviews": True,
        "reassignConversation": True,
        "surveys": True,
    }


def default_member_permissions() -> dict:
    return {
        "broadcasts": True,
        "campaigns": True,
        "textBot": True,
        "triggers": True,
        "reportingAndAnalytics": False,
        "dataAndSecurity": False,
        "inbox": False,
        "members": False,
        "billing": False,
        "manualOptIn": True,
        "phoneChecker": True,
        "contactCreate": True,
        "transferConversation": False,
        "contactAccess": "can_access_all",
        "cannedMessage": True,
        "reviews": True,
        "reassignConversation": True,
        "surveys": True,
    }


def default_manager_permissions() -> dict:
    return {
        "broadcasts": True,
        "campaigns": True,
        "textBot": True,
        "triggers": True,
        "reportingAndAnalytics": True,
        "dataAndSecurity": True,
        "inbox": True,
        "members": False,
        "billing": False,
        "manualOptIn": True,
        "phoneChecker": True,
        "contactCreate": True,
        "transferConversation": False,
        "contactAccess": "can_access_all",
        "cannedMessage": True,
        "reviews": True,
        "reassignConversation": True,
        "surveys": True,
    }
