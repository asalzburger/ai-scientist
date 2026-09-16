from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..communications.models import email_address, header
from ..domain import new_id


class Contact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(default_factory=lambda: new_id("CONTACT"))
    name: str = Field(min_length=1)
    email: str
    timezone: str = "UTC"
    _email = field_validator("email")(email_address)
    _name = field_validator("name")(header)

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        from zoneinfo import ZoneInfo

        ZoneInfo(value)
        return value
