"""Typed test data shapes.

These are pydantic models rather than bare annotations, so a malformed account file fails at
load time with the offending field named instead of halfway through a test.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CustomFieldType = Literal[
    "Text",
    "Number",
    "Date",
    "URL",
    "Date & Time",
    "First Name",
    "Last Name",
    "Phone",
    "Email",
    "Owner",
]
NewCustomFieldType = Literal["text", "url", "number", "date", "datetime"]
Role = Literal["Owner", "Admin", "Manager", "Member"]
TagAlertType = Literal["exist", "long"]
Visibility = Literal["Myself only", "All members"]


class NewMember(BaseModel):
    """The seeded second user on every account, whose role the parametrized tests switch."""

    email: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    password: str = ""
    url: str | None = None


class NewContact(BaseModel):
    """Payload for POST /contacts. Only the phone number is mandatory."""

    phone: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class ProtectedNumber(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str | None = None
    type: str | None = None
    formatted: str | None = None
    id: int | None = None


class ProtectedBlock(BaseModel):
    """Numbers and inboxes cleanup must never delete - they belong to the permanent account.

    default_factory=list, not `= []`: a mutable default would be shared by every instance.
    """

    numbers: list[ProtectedNumber] = Field(default_factory=list)
    inboxes: list[str] = Field(default_factory=list)


class RegistrationData(BaseModel):
    """One provisioned account, loaded from variables/accounts/account{N}.json.

    The files use camelCase while the code uses snake_case; `Field(alias=...)` bridges the two,
    so pydantic reads "firstName" and exposes it as `.first_name`.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    email: str
    password: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    organization_id: int = Field(alias="organizationId")
    phone: str = ""
    account: str = ""
    business_number: str = Field(default="", alias="businessNumber")
    token: str = ""
    member: NewMember | None = None
    protected: ProtectedBlock | None = None


class CustomField(BaseModel):
    """A custom field as the UI shows it."""

    name: str
    type: CustomFieldType
    show: bool


class NewCustomField(BaseModel):
    """A custom field as the API takes it - lowercase type, `visible` instead of `show`."""

    name: str
    type: NewCustomFieldType
    visible: bool


class TagData(BaseModel):
    """One row of the tags table. `contact` is the counter, read from the cell as text."""

    tag_name: str
    contact: str
