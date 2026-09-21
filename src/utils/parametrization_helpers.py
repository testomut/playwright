"""Role-parametrized sign-in.

The same test often has to pass as Owner, Admin, Manager and Member. Rather than writing it
four times, the test is parametrized over ROLES and calls oauth_by_role:

    @pytest.mark.parametrize("role", ROLES)
    def test_create_tag_by_role(role, ...):
        oauth_by_role(api_request, user_details, role, tags_page)

Role parameterization expands one scenario into multiple independently reported cases.
"""

from __future__ import annotations

from src.constants.default_role_permissions import (
    default_admin_permissions,
    default_manager_permissions,
    default_member_permissions,
)
from src.pages.base_page import BasePage
from src.types.models import RegistrationData, Role
from src.utils.api_requests import ApiRequests

ROLES: tuple[Role, ...] = ("Owner", "Admin", "Manager", "Member")


def oauth_by_role(
    api_request: ApiRequests,
    user_details: RegistrationData,
    role: Role,
    page: BasePage,
) -> None:
    """Re-authenticate the browser as the seeded member with the given role.

    Each account file carries two users: the owner and one seeded member. There is no separate
    admin or manager account - the member's role is flipped to whatever the test needs.

    For any role but Owner:
      1. clear cookies and localStorage, so the owner session is really gone;
      2. sign in as the member;
      3. change their role over the *owner's* token - a member cannot promote themselves;
      4. sign in again, because the role is baked into the JWT and the session from step 2
         still carries the old one.

    Step 4 is the easy one to miss: skip it and the browser keeps the previous role while the
    backend reports the new one, which fails in a thoroughly confusing way. Neither login
    passes a token file, because a cached token would still carry the previous role.
    """
    if role == "Owner":
        return

    assert user_details.member is not None, "the account file has no seeded member"
    member = user_details.member

    page.clear_cache_cookies()
    page.oauth_with_token(api_request.login(member.email, member.password))

    members = api_request.get_members(user_details.token)
    member_id = next((m["id"] for m in members if m["email"] == member.email), None)

    if member_id is None:
        raise ValueError("Seeded member not found")

    if role == "Admin":
        api_request.update_user_role(user_details.token, member_id, "admin", default_admin_permissions())
    elif role == "Manager":
        api_request.update_user_role(user_details.token, member_id, "manager", default_manager_permissions())

    elif role == "Member":
        api_request.update_user_role(user_details.token, member_id, "member", default_member_permissions())

    page.oauth_with_token(api_request.login(member.email, member.password))
