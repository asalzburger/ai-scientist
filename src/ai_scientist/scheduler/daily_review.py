from __future__ import annotations

from ..agent import ScientistAgent


def run_daily_review(agent: ScientistAgent) -> str:
    prompt = (agent.settings.root / "prompts/daily_review.md").read_text(encoding="utf-8")
    return agent.ask(prompt)

