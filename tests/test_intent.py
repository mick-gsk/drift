"""TDD tests for Phase B — Intent Layer.

Tests cover:
1. Contract model (IntentContract, Requirement, Constraint, IntentCategory)
2. LLM client abstraction (template fallback)
3. Intent classification (keyword-based fallback)
4. Clarifying question generation
5. Contract storage (YAML round-trip)
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ── 1. Contract Model ──────────────────────────────────────────────────


class TestIntentCategory:
    """IntentCategory enum covers core app archetypes."""

    def test_category_is_str_enum(self) -> None:
        from drift.intent.models import IntentCategory

        assert issubclass(IntentCategory, str)
        # Must have at least these core categories
        expected = {
            "data_persistence",
            "crud",
            "auth",
            "realtime",
            "api",
            "automation",
        }
        actual = {c.value for c in IntentCategory}
        assert expected.issubset(actual), f"Missing categories: {expected - actual}"


class TestRequirement:
    """Requirement captures a single formalized need."""

    def test_fields(self) -> None:
        from drift.intent.models import Requirement

        req = Requirement(
            id="req-1",
            description_plain="Die App soll Daten speichern",
            description_technical="Persistent storage layer required",
            priority="must",
        )
        assert req.id == "req-1"
        assert req.description_plain == "Die App soll Daten speichern"
        assert req.description_technical == "Persistent storage layer required"
        assert req.priority == "must"
        assert req.validation_signal is None  # optional

    def test_with_validation_signal(self) -> None:
        from drift.intent.models import Requirement

        req = Requirement(
            id="req-2",
            description_plain="Fehlermeldungen zeigen",
            description_technical="Guard clauses on user input",
            priority="should",
            validation_signal="guard_clause_deficit",
        )
        assert req.validation_signal == "guard_clause_deficit"

    def test_priority_literal(self) -> None:
        from drift.intent.models import Requirement

        # Invalid priority should raise
        with pytest.raises((ValueError, TypeError)):
            Requirement(
                id="req-bad",
                description_plain="x",
                description_technical="x",
                priority="invalid",  # type: ignore[arg-type]
            )


class TestConstraint:
    """Constraint captures non-functional requirements."""

    def test_fields(self) -> None:
        from drift.intent.models import Constraint

        c = Constraint(
            id="con-1",
            description="Muss offline funktionieren",
        )
        assert c.id == "con-1"
        assert c.description == "Muss offline funktionieren"


class TestIntentContract:
    """IntentContract is the full formalized intent."""

    def test_creation(self) -> None:
        from drift.intent.models import IntentCategory, IntentContract, Requirement

        contract = IntentContract(
            description="Ich will eine Kühlschrank-App die mein Essen trackt",
            category=IntentCategory.DATA_PERSISTENCE,
            requirements=[
                Requirement(
                    id="req-1",
                    description_plain="Essen hinzufügen und entfernen",
                    description_technical="CRUD operations on food items",
                    priority="must",
                ),
            ],
            language="de",
        )
        assert contract.id  # auto-generated UUID
        assert contract.description.startswith("Ich will")
        assert contract.category == IntentCategory.DATA_PERSISTENCE
        assert len(contract.requirements) == 1
        assert contract.language == "de"
        assert contract.created_at is not None
        assert contract.constraints == []  # default empty

    def test_id_is_uuid(self) -> None:
        import uuid

        from drift.intent.models import IntentCategory, IntentContract

        contract = IntentContract(
            description="test",
            category=IntentCategory.CRUD,
            requirements=[],
            language="en",
        )
        # Should be valid UUID
        parsed = uuid.UUID(contract.id)
        assert str(parsed) == contract.id

    def test_serialization_roundtrip(self) -> None:
        """Contract serializes to dict and back."""
        from drift.intent.models import IntentCategory, IntentContract, Requirement

        contract = IntentContract(
            description="Eine REST API für Rezepte",
            category=IntentCategory.API,
            requirements=[
                Requirement(
                    id="req-1",
                    description_plain="Rezepte abrufen",
                    description_technical="GET endpoint for recipes",
                    priority="must",
                    validation_signal="missing_authorization",
                ),
            ],
            language="de",
        )
        d = contract.to_dict()
        assert isinstance(d, dict)
        assert d["description"] == "Eine REST API für Rezepte"
        assert d["category"] == "api"
        assert len(d["requirements"]) == 1
        assert d["requirements"][0]["validation_signal"] == "missing_authorization"

        # Roundtrip
        restored = IntentContract.from_dict(d)
        assert restored.id == contract.id
        assert restored.category == contract.category
        assert restored.requirements[0].id == "req-1"


# ── 2. LLM Client Abstraction ──────────────────────────────────────────


class TestLLMFallback:
    """Without LLM, the template-based fallback works."""

    def test_fallback_classify_returns_category(self) -> None:
        from drift.intent._classify import classify_intent_fallback

        result = classify_intent_fallback(
            "Ich will eine App die meine Daten in einer Datenbank speichert"
        )
        assert result.category is not None
        assert len(result.requirements) > 0

    def test_fallback_handles_empty_input(self) -> None:
        from drift.intent._classify import classify_intent_fallback

        result = classify_intent_fallback("")
        assert result.category is not None  # default category
        assert result.requirements == []

    def test_llm_not_available_graceful(self) -> None:
        """When litellm is not configured, classify uses fallback."""
        from drift.intent._classify import classify_intent

        # Without LLM config, should gracefully fall back
        result = classify_intent(
            "Eine Todo-App mit Login",
            language="de",
            llm_config=None,
        )
        assert result.category is not None
        assert result.description == "Eine Todo-App mit Login"


# ── 3. Intent Classification ──────────────────────────────────────────


class TestClassifyIntent:
    """Keyword-based fallback classification."""

    def test_data_keywords(self) -> None:
        from drift.intent._classify import classify_intent_fallback
        from drift.intent.models import IntentCategory

        result = classify_intent_fallback("App die Daten speichert und lädt")
        assert result.category in {
            IntentCategory.DATA_PERSISTENCE,
            IntentCategory.CRUD,
        }

    def test_auth_keywords(self) -> None:
        from drift.intent._classify import classify_intent_fallback
        from drift.intent.models import IntentCategory

        result = classify_intent_fallback("Login und Passwort-Verwaltung")
        assert result.category == IntentCategory.AUTH

    def test_api_keywords(self) -> None:
        from drift.intent._classify import classify_intent_fallback
        from drift.intent.models import IntentCategory

        result = classify_intent_fallback("REST API endpoint for user management")
        assert result.category == IntentCategory.API

    def test_automation_keywords(self) -> None:
        from drift.intent._classify import classify_intent_fallback
        from drift.intent.models import IntentCategory

        result = classify_intent_fallback("Script das automatisch Backups macht")
        assert result.category == IntentCategory.AUTOMATION

    def test_realtime_keywords(self) -> None:
        from drift.intent._classify import classify_intent_fallback
        from drift.intent.models import IntentCategory

        result = classify_intent_fallback("Chat-App mit Echtzeit-Updates und WebSocket")
        assert result.category == IntentCategory.REALTIME

    def test_requirements_generated(self) -> None:
        """Classification generates at least one requirement for non-empty input."""
        from drift.intent._classify import classify_intent_fallback

        result = classify_intent_fallback("Rezept-Verwaltung mit Suchfunktion")
        assert len(result.requirements) >= 1
        assert all(r.id for r in result.requirements)
        assert all(r.description_plain for r in result.requirements)


# ── 4. Clarifying Questions ──────────────────────────────────────────


class TestClarifyingQuestions:
    """Question generator finds gaps in intent contracts."""

    def test_generates_questions_for_incomplete_contract(self) -> None:
        from drift.intent._questions import generate_questions
        from drift.intent.models import IntentCategory, IntentContract, Requirement

        contract = IntentContract(
            description="Eine App die Daten speichert",
            category=IntentCategory.DATA_PERSISTENCE,
            requirements=[
                Requirement(
                    id="req-1",
                    description_plain="Daten speichern",
                    description_technical="Persist data",
                    priority="must",
                ),
            ],
            language="de",
        )
        questions = generate_questions(contract)
        assert isinstance(questions, list)
        assert len(questions) >= 1
        assert len(questions) <= 3  # max 3 questions

    def test_question_has_required_fields(self) -> None:
        from drift.intent._questions import generate_questions
        from drift.intent.models import IntentCategory, IntentContract, Requirement

        contract = IntentContract(
            description="Eine Todo-App",
            category=IntentCategory.CRUD,
            requirements=[
                Requirement(
                    id="req-1",
                    description_plain="Todos anlegen",
                    description_technical="Create todo items",
                    priority="must",
                ),
            ],
            language="de",
        )
        questions = generate_questions(contract)
        for q in questions:
            assert q.question_text  # non-empty
            assert isinstance(q.options, list)
            assert q.affects_requirement  # which requirement it clarifies

    def test_empty_requirements_still_generates(self) -> None:
        from drift.intent._questions import generate_questions
        from drift.intent.models import IntentCategory, IntentContract

        contract = IntentContract(
            description="Irgendeine App",
            category=IntentCategory.CRUD,
            requirements=[],
            language="de",
        )
        questions = generate_questions(contract)
        assert len(questions) >= 1  # should ask about basic requirements


# ── 5. Contract Storage ──────────────────────────────────────────────


class TestContractStorage:
    """YAML-based contract persistence."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        from drift.intent._store import load_contracts, save_contract
        from drift.intent.models import IntentCategory, IntentContract, Requirement

        contract = IntentContract(
            description="Kühlschrank-Manager",
            category=IntentCategory.DATA_PERSISTENCE,
            requirements=[
                Requirement(
                    id="req-1",
                    description_plain="Essen tracken",
                    description_technical="CRUD for food items",
                    priority="must",
                    validation_signal="guard_clause_deficit",
                ),
            ],
            language="de",
        )

        save_contract(contract, tmp_path)
        loaded = load_contracts(tmp_path)
        assert len(loaded) == 1
        assert loaded[0].id == contract.id
        assert loaded[0].category == IntentCategory.DATA_PERSISTENCE
        assert loaded[0].requirements[0].validation_signal == "guard_clause_deficit"

    def test_append_multiple_contracts(self, tmp_path: Path) -> None:
        from drift.intent._store import load_contracts, save_contract
        from drift.intent.models import IntentCategory, IntentContract

        c1 = IntentContract(
            description="App 1",
            category=IntentCategory.CRUD,
            requirements=[],
            language="en",
        )
        c2 = IntentContract(
            description="App 2",
            category=IntentCategory.API,
            requirements=[],
            language="de",
        )
        save_contract(c1, tmp_path)
        save_contract(c2, tmp_path)

        loaded = load_contracts(tmp_path)
        assert len(loaded) == 2
        assert {c.description for c in loaded} == {"App 1", "App 2"}

    def test_load_from_empty_dir(self, tmp_path: Path) -> None:
        from drift.intent._store import load_contracts

        loaded = load_contracts(tmp_path)
        assert loaded == []

    def test_storage_file_is_yaml(self, tmp_path: Path) -> None:
        from drift.intent._store import INTENT_FILENAME, save_contract
        from drift.intent.models import IntentCategory, IntentContract

        contract = IntentContract(
            description="Test",
            category=IntentCategory.CRUD,
            requirements=[],
            language="en",
        )
        save_contract(contract, tmp_path)
        intent_file = tmp_path / INTENT_FILENAME
        assert intent_file.exists()
        content = intent_file.read_text(encoding="utf-8")
        assert "description:" in content or "- description:" in content
