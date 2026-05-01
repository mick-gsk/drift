"""Clarifying question generator for intent contracts.

Analyzes an IntentContract for gaps and generates up to 3 questions
to help the user refine their intent.
"""

from __future__ import annotations

from drift_engine.intent.models import (
    ClarifyingQuestion,
    IntentCategory,
    IntentContract,
)

# ---------------------------------------------------------------------------
# Gap detection rules: category → questions about missing aspects
# ---------------------------------------------------------------------------

_GAP_QUESTIONS: dict[IntentCategory, list[ClarifyingQuestion]] = {
    IntentCategory.DATA_PERSISTENCE: [
        ClarifyingQuestion(
            question_text="Sollen mehrere Personen gleichzeitig auf die Daten zugreifen können?",
            options=["Ja, mehrere Nutzer", "Nein, nur ich", "Weiß ich noch nicht"],
            affects_requirement="multi_user",
        ),
        ClarifyingQuestion(
            question_text="Soll die App auch ohne Internet funktionieren?",
            options=["Ja, offline-fähig", "Nein, nur online", "Weiß ich noch nicht"],
            affects_requirement="offline",
        ),
        ClarifyingQuestion(
            question_text="Wie wichtig ist es, dass keine Daten verloren gehen?",
            options=["Sehr wichtig — Backups nötig", "Normal reicht", "Nicht so wichtig"],
            affects_requirement="data_safety",
        ),
    ],
    IntentCategory.CRUD: [
        ClarifyingQuestion(
            question_text="Brauchen die Einträge eine Suchfunktion?",
            options=["Ja", "Nein", "Weiß ich noch nicht"],
            affects_requirement="search",
        ),
        ClarifyingQuestion(
            question_text="Sollen gelöschte Einträge wiederherstellbar sein?",
            options=["Ja, Papierkorb", "Nein, sofort löschen", "Weiß ich noch nicht"],
            affects_requirement="soft_delete",
        ),
        ClarifyingQuestion(
            question_text="Wer darf Einträge bearbeiten?",
            options=["Jeder", "Nur der Ersteller", "Nur bestimmte Rollen"],
            affects_requirement="access_control",
        ),
    ],
    IntentCategory.AUTH: [
        ClarifyingQuestion(
            question_text="Soll es verschiedene Benutzerrollen geben (z.B. Admin, Nutzer)?",
            options=["Ja", "Nein, alle gleich", "Weiß ich noch nicht"],
            affects_requirement="roles",
        ),
        ClarifyingQuestion(
            question_text="Soll Login über externe Anbieter möglich sein (Google, GitHub)?",
            options=["Ja", "Nein, nur eigene Anmeldung", "Weiß ich noch nicht"],
            affects_requirement="oauth",
        ),
    ],
    IntentCategory.REALTIME: [
        ClarifyingQuestion(
            question_text="Wie viele Nutzer sollen gleichzeitig verbunden sein können?",
            options=["Wenige (< 10)", "Mittel (10-100)", "Viele (> 100)"],
            affects_requirement="scale",
        ),
        ClarifyingQuestion(
            question_text="Müssen verpasste Nachrichten nachgeliefert werden?",
            options=["Ja, nichts darf verloren gehen", "Nein, nur live", "Weiß ich noch nicht"],
            affects_requirement="message_persistence",
        ),
    ],
    IntentCategory.API: [
        ClarifyingQuestion(
            question_text="Wer soll die Schnittstelle nutzen können?",
            options=["Nur eigene Apps", "Externe Entwickler", "Öffentlich für alle"],
            affects_requirement="api_access",
        ),
        ClarifyingQuestion(
            question_text="Braucht die Schnittstelle Authentifizierung?",
            options=["Ja, API-Key oder Token", "Nein, öffentlich", "Weiß ich noch nicht"],
            affects_requirement="api_auth",
        ),
    ],
    IntentCategory.AUTOMATION: [
        ClarifyingQuestion(
            question_text="Wie oft soll die Automatisierung laufen?",
            options=["Einmalig", "Regelmäßig (z.B. täglich)", "Bei bestimmten Ereignissen"],
            affects_requirement="schedule",
        ),
        ClarifyingQuestion(
            question_text="Was soll passieren, wenn die Automatisierung fehlschlägt?",
            options=["Benachrichtigung senden", "Automatisch wiederholen", "Nichts — einfach stoppen"],  # noqa: E501
            affects_requirement="error_handling",
        ),
    ],
    IntentCategory.GENERAL: [
        ClarifyingQuestion(
            question_text="Was für eine Art von Anwendung soll es werden?",
            options=["Web-App", "Kommandozeilen-Tool", "Hintergrund-Service", "Etwas anderes"],
            affects_requirement="app_type",
        ),
        ClarifyingQuestion(
            question_text="Wer soll die Anwendung nutzen?",
            options=["Nur ich selbst", "Ein kleines Team", "Viele externe Nutzer"],
            affects_requirement="audience",
        ),
    ],
}


def generate_questions(
    contract: IntentContract,
    *,
    max_questions: int = 3,
) -> list[ClarifyingQuestion]:
    """Generate clarifying questions for gaps in an intent contract.

    Parameters
    ----------
    contract:
        The preliminary intent contract to analyze.
    max_questions:
        Maximum number of questions to return.

    Returns
    -------
    list[ClarifyingQuestion]
        Up to *max_questions* questions for the user.
    """
    questions = _GAP_QUESTIONS.get(contract.category, _GAP_QUESTIONS[IntentCategory.GENERAL])

    # Filter out questions that are already covered by existing requirements
    existing_affects = {r.id.replace("req-auto-", "") for r in contract.requirements}

    filtered: list[ClarifyingQuestion] = []
    for q in questions:
        if q.affects_requirement not in existing_affects:
            filtered.append(q)

    return filtered[:max_questions]
