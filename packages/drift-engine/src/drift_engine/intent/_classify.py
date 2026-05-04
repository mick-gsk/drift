"""Intent classification — keyword fallback and LLM-based classification."""

from __future__ import annotations

import re
from typing import Any

from drift_engine.intent.models import IntentCategory, IntentContract, Requirement

# ---------------------------------------------------------------------------
# Keyword patterns → category mapping (ordered by specificity)
# ---------------------------------------------------------------------------

_KEYWORD_RULES: list[tuple[re.Pattern[str], IntentCategory]] = [
    # Auth patterns
    (
        re.compile(
            r"(?:login|passwort|password|auth|authentif|registrier|sign.?up|sign.?in|berechtigung|permission|zugriff)",
            re.IGNORECASE,
        ),
        IntentCategory.AUTH,
    ),
    # Realtime patterns
    (
        re.compile(
            r"(?:echtzeit|realtime|real.?time|websocket|live.?update|chat|stream|push.?notification)",
            re.IGNORECASE,
        ),
        IntentCategory.REALTIME,
    ),
    # API patterns
    (
        re.compile(
            r"(?:rest\s?api|graphql|endpoint|http|webhook|microservice|service.?schnittstelle)",
            re.IGNORECASE,
        ),
        IntentCategory.API,
    ),
    # Automation patterns
    (
        re.compile(
            r"(?:automat|script|cron|schedule|batch|pipeline|ci.?cd|deploy|backup)",
            re.IGNORECASE,
        ),
        IntentCategory.AUTOMATION,
    ),
    # Data persistence (before CRUD, more specific)
    (
        re.compile(
            r"(?:datenbank|database|persist|speicher|storage|sql|mongo|redis|cache)",
            re.IGNORECASE,
        ),
        IntentCategory.DATA_PERSISTENCE,
    ),
    # CRUD patterns
    (
        re.compile(
            r"(?:crud|erstell|anlegen|create|l[öo]sch|delete|bearbeit|edit|update|verwalt|manage|hinzuf[üu]g|entfern|list|auflist)",
            re.IGNORECASE,
        ),
        IntentCategory.CRUD,
    ),
]

# ---------------------------------------------------------------------------
# Category → default requirement templates
# ---------------------------------------------------------------------------

_CATEGORY_TEMPLATES: dict[IntentCategory, list[dict[str, str]]] = {
    IntentCategory.DATA_PERSISTENCE: [
        {
            "plain": "Daten werden dauerhaft gespeichert",
            "technical": "Persistent storage layer for application data",
            "signal": "exception_contract_drift",
        },
    ],
    IntentCategory.CRUD: [
        {
            "plain": "Einträge erstellen, lesen, ändern und löschen",
            "technical": "Full CRUD operations on domain entities",
            "signal": "guard_clause_deficit",
        },
    ],
    IntentCategory.AUTH: [
        {
            "plain": "Nutzer können sich anmelden und abmelden",
            "technical": "Authentication flow with session management",
            "signal": "missing_authorization",
        },
        {
            "plain": "Nur berechtigte Nutzer haben Zugriff",
            "technical": "Authorization checks on protected resources",
            "signal": "missing_authorization",
        },
    ],
    IntentCategory.REALTIME: [
        {
            "plain": "Änderungen werden sofort sichtbar",
            "technical": "Real-time data synchronization via WebSocket or SSE",
            "signal": "exception_contract_drift",
        },
    ],
    IntentCategory.API: [
        {
            "plain": "Daten über eine Schnittstelle bereitstellen",
            "technical": "RESTful or GraphQL API endpoints",
            "signal": "missing_authorization",
        },
    ],
    IntentCategory.AUTOMATION: [
        {
            "plain": "Aufgaben werden automatisch ausgeführt",
            "technical": "Automated task execution with scheduling",
            "signal": "broad_exception_monoculture",
        },
    ],
}


def classify_intent_fallback(description: str) -> IntentContract:
    """Classify an intent using keyword matching (no LLM required).

    Parameters
    ----------
    description:
        Free-text description of the user's intent.

    Returns
    -------
    IntentContract
        Preliminary contract with category and auto-generated requirements.
    """
    if not description.strip():
        return IntentContract(
            description=description,
            category=IntentCategory.GENERAL,
            requirements=[],
            language="de",
        )

    # Match against keyword rules
    category = IntentCategory.GENERAL
    for pattern, cat in _KEYWORD_RULES:
        if pattern.search(description):
            category = cat
            break

    # Generate requirements from category templates
    templates = _CATEGORY_TEMPLATES.get(category, [])
    requirements: list[Requirement] = []
    for i, tpl in enumerate(templates, 1):
        requirements.append(
            Requirement(
                id=f"req-auto-{i}",
                description_plain=tpl["plain"],
                description_technical=tpl["technical"],
                priority="must",
                validation_signal=tpl.get("signal"),
            )
        )

    return IntentContract(
        description=description,
        category=category,
        requirements=requirements,
        language="de",
    )


def classify_intent(
    description: str,
    *,
    language: str = "de",
    llm_config: dict[str, Any] | None = None,
) -> IntentContract:
    """Classify an intent, using LLM if configured, fallback otherwise.

    Parameters
    ----------
    description:
        Free-text description of the user's intent.
    language:
        ISO 639-1 language code for the contract.
    llm_config:
        Optional LLM configuration dict. If ``None``, uses keyword fallback.

    Returns
    -------
    IntentContract
        Formalized intent contract.
    """
    if llm_config is None:
        contract = classify_intent_fallback(description)
        contract.language = language
        return contract

    # LLM path — future implementation
    # For now, always use fallback
    contract = classify_intent_fallback(description)
    contract.language = language
    return contract
