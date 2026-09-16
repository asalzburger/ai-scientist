from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    db_path: Path
    identity_path: Path
    policy_path: Path
    model: str

    @classmethod
    def load(cls, root: Path | None = None) -> Settings:
        project_root = (root or Path.cwd()).resolve()
        return cls(
            root=project_root,
            db_path=project_root / os.getenv("AI_SCIENTIST_DB", "state/scientist.db"),
            identity_path=project_root
            / os.getenv("AI_SCIENTIST_IDENTITY", "config/identity.yaml"),
            policy_path=project_root
            / os.getenv("AI_SCIENTIST_POLICY", "config/policies.yaml"),
            model=os.getenv("AI_SCIENTIST_MODEL", "gpt-6-astra"),
        )


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"Expected mapping in {path}")
    return data
