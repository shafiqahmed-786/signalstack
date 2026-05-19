"""
app/orchestration/prompts/registry.py

Versioned prompt registry.

Every prompt in the system is registered here with a version string,
the target model, and a hash of the expected output schema.

This enables:
  1. Report reproducibility: every saved report stores prompt versions,
     so you can identify which prompt produced any report and replay it.
  2. Regression detection: if you change a prompt, bump the version.
     Reports generated with the old version are identifiable by their
     stored generation_context.planner_prompt_version field.
  3. Schema drift detection: output_schema_hash catches cases where the
     prompt was updated to target a new schema without bumping the version.

Usage:
    from app.orchestration.prompts.registry import get_prompt, PromptVersion

    planner_prompt = get_prompt("planner")
    synthesizer_prompt = get_prompt("synthesizer")
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.orchestration.prompts.planner_v1 import (
    PLANNER_SYSTEM_V1,
    PLANNER_USER_TEMPLATE_V1,
)
from app.orchestration.prompts.synthesizer_v1 import (
    SYNTHESIZER_SYSTEM_V1,
    SYNTHESIZER_USER_TEMPLATE_V1,
)


@dataclass(frozen=True)
class PromptVersion:
    """
    A versioned prompt pair (system + user template).

    name              — logical name, used as the registry key
    version           — semver string: "1.0.0"
    model             — the Claude model this prompt was tuned for
    system            — system prompt string
    user_template     — Jinja2 template string for the user turn
    output_schema_hash — SHA-256 of the JSON schema the prompt targets
                         (helps detect schema drift without version bumps)
    created_at        — ISO date when this version was authored
    """

    name: str
    version: str
    model: str
    system: str
    user_template: str
    output_schema_hash: str
    created_at: str

    @property
    def full_version(self) -> str:
        """Canonical version string for storage: "name:version"."""
        return f"{self.name}:{self.version}"

    @staticmethod
    def _hash_text(text: str) -> str:
        return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


def _compute_report_schema_hash() -> str:
    """
    Compute a short hash of the ResearchReport JSON schema.
    Imported lazily to avoid circular imports at module load.
    """
    from app.models.domain.report_output import ResearchReport
    import json

    schema_str = json.dumps(ResearchReport.model_json_schema(), sort_keys=True)
    return "sha256:" + hashlib.sha256(schema_str.encode()).hexdigest()[:16]


def _compute_plan_schema_hash() -> str:
    """Short hash representing the expected structure of the Planner's output."""
    plan_fields = "companies,query_intent,tools_needed,reasoning"
    return "sha256:" + hashlib.sha256(plan_fields.encode()).hexdigest()[:16]


# ── Registry ──────────────────────────────────────────────────────────────────

PROMPT_REGISTRY: dict[str, PromptVersion] = {
    "planner": PromptVersion(
        name="planner",
        version="1.0.0",
        model="claude-sonnet-4-20250514",
        system=PLANNER_SYSTEM_V1,
        user_template=PLANNER_USER_TEMPLATE_V1,
        output_schema_hash=_compute_plan_schema_hash(),
        created_at="2025-05-14",
    ),
    "synthesizer": PromptVersion(
        name="synthesizer",
        version="1.0.0",
        model="claude-sonnet-4-20250514",
        system=SYNTHESIZER_SYSTEM_V1,
        user_template=SYNTHESIZER_USER_TEMPLATE_V1,
        output_schema_hash=_compute_report_schema_hash(),
        created_at="2025-05-14",
    ),
}


def get_prompt(name: str) -> PromptVersion:
    """
    Retrieve a PromptVersion from the registry by name.

    Raises ValueError if the name is not registered.
    """
    if name not in PROMPT_REGISTRY:
        available = ", ".join(f"'{k}'" for k in PROMPT_REGISTRY)
        raise ValueError(
            f"Unknown prompt name: {name!r}. Available prompts: {available}"
        )
    return PROMPT_REGISTRY[name]


def list_prompts() -> list[str]:
    """Returns all registered prompt names."""
    return list(PROMPT_REGISTRY.keys())