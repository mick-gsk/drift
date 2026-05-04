# ReviewerAgentProtocol Contract

**Feature 005 — Evidence-Based Drift Verification**

---

## Zweck

Definiert den Protokoll-Vertrag zwischen `src/drift/verify/_checker.py` und der `ReviewerAgentProtocol`-Schnittstelle. Abstrahiert den unabhängigen Reviewer-Agent so, dass in Tests ein `MockReviewerAgent` injiziert werden kann.

---

## Protocol Definition

```python
from typing import Protocol
from drift.verify._models import ChangeSet, IndependentReviewResult

class ReviewerAgentProtocol(Protocol):
    def review(
        self,
        change_set: ChangeSet,
        preliminary_violations: list[ViolationFinding],
        timeout_seconds: int = 60,
    ) -> IndependentReviewResult:
        """
        Führt einen unabhängigen Review in einem frischen Kontext durch.

        Args:
            change_set: Das zu prüfende Change-Set.
            preliminary_violations: Violations aus dem deterministischen Check.
            timeout_seconds: Maximale Wartezeit. Bei Überschreitung muss
                             IndependentReviewResult(available=False, ...) zurückgegeben
                             werden — KEIN Exception-Raise.

        Returns:
            IndependentReviewResult mit available=True bei Erfolg,
            available=False bei Timeout oder Fehler.
        """
        ...
```

---

## Fallback-Vertrag (Timeout/Fehler)

Ein `ReviewerAgentProtocol`-Implementierer MUSS bei Timeout oder jedem internen Fehler folgendes zurückgeben (statt Exception zu raisen):

```python
IndependentReviewResult(
    available=False,
    confidence_delta=0.0,
    findings=[],
    spec_criteria_violated=[],
)
```

Der Aufrufer ergänzt dann `EvidenceFlag.independent_review_unavailable` im `EvidencePackage.flags`.

---

## MockReviewerAgent (Test-Implementierung)

```python
class MockReviewerAgent:
    def __init__(self, result: IndependentReviewResult):
        self._result = result

    def review(self, change_set, preliminary_violations, timeout_seconds=60):
        return self._result
```

Verwendung in Tests: immer über `MockReviewerAgent` — kein echter LLM-Call in der Test-Suite.

---

## Wiring im ProductionCode

`src/drift/verify/_reviewer.py` enthält die Produktions-Implementierung (`DriftMcpReviewerAgent`), die den `drift_nudge`-MCP-Endpoint als Review-Proxy verwendet. Diese Implementierung ist optional (`[reviewer]` extra in `pyproject.toml`); ohne sie wird `MockReviewerAgent(result=unavailable)` als Default genommen.
