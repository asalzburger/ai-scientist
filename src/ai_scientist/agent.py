from __future__ import annotations

from typing import Any

from .communications.preferences import CommunicationPreferences
from .config import Settings, load_yaml
from .context import ContextBuilder
from .storage import SQLiteStore


class ScientistAgent:
    def __init__(self, settings: Settings, store: SQLiteStore):
        self.settings = settings
        self.store = store
        self.identity = load_yaml(settings.identity_path)

    def instructions(self) -> str:
        template = (self.settings.root / "prompts/scientist.md").read_text(encoding="utf-8")
        instructions = template.format(
            name=self.identity["name"],
            group=self.identity["group"],
            mission=self.identity["mission"],
        )
        preferences = CommunicationPreferences.model_validate(
            load_yaml(self.settings.root / "config/communication.yaml")
        )
        communication = (self.settings.root / "prompts/communication.md").read_text(
            encoding="utf-8"
        )
        return (
            instructions
            + "\n\n"
            + communication
            + "\n\nCommunication preferences:\n"
            + preferences.model_dump_json()
        )

    def ask(self, question: str, client: Any | None = None) -> str:
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        context = ContextBuilder(self.store).render()
        response = client.responses.create(
            model=self.settings.model,
            instructions=self.instructions(),
            input=f"Authoritative state snapshot:\n{context}\n\nTeam member request:\n{question}",
        )
        self.store.audit(
            actor=self.identity["name"],
            action="model_response",
            outcome="completed",
            details={"model": self.settings.model},
        )
        return response.output_text
