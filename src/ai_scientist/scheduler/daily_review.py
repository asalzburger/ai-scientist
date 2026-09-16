from __future__ import annotations

from ..agent import ScientistAgent
from .models import DailyBriefing


def run_daily_review(agent: ScientistAgent) -> str:
    prompt = (agent.settings.root / "prompts/daily_review.md").read_text(encoding="utf-8")
    body = agent.ask(prompt)
    briefing = DailyBriefing(body=body)
    agent.store.save_document("daily_briefing", briefing.id, briefing.model_dump(mode="json"))
    return body
