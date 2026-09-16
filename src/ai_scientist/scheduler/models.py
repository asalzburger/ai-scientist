from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain import new_id


class DailyBriefing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(default_factory=lambda: new_id("BRIEFING"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["draft"] = "draft"
    body: str
