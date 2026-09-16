from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Operation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    action: Literal["send_email", "modify_calendar"]
    target: str
    fingerprint: str
    payload: dict
    status: Literal["pending", "approved", "executing", "succeeded", "uncertain", "revoked"] = (
        "pending"
    )
    expires_at: datetime
    token_hash: str | None = None
    receipt: str | None = None
