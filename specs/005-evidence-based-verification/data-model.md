# Data Model: Evidence-Based Drift Verification

**Phase 1 Output** | Feature 005 | 2026-05-01

---

## Entities

### ChangeSet

Die zu prüfende Eingabe. Wird vom Aufrufer übergeben.

```
ChangeSet (frozen Pydantic model)
├── diff_text: str                  # Unified diff als Text (kann leer sein)
├── changed_files: list[Path]       # Optional: explizite Dateiliste
├── spec_path: Path | None          # Optionaler Pfad zu spec.md für Confidence-Check
├── repo_path: Path                 # Wurzel des analysierten Repos
├── author: str | None
└── created_at: datetime
```

**State transitions**: Kein eigener Zustand; dient als Input-Value-Object.

---

### EvidencePackage

Das zentrale Ergebnis-Artefakt. Unveränderlich nach Erstellung.

```
EvidencePackage (frozen Pydantic model)
├── schema: str = "evidence-package-v1"
├── version: str                    # drift-version
├── change_set_id: str              # sha256 des diff_text (leer → "empty")
├── repo: str                       # repo_path.as_posix()
├── verified_at: datetime
├── drift_score: float              # 0.0–1.0; aus deterministischem Check
├── spec_confidence_score: float    # 0.0–1.0; passed_checks / total_checks
├── action_recommendation: ActionRecommendation
├── violations: list[ViolationFinding]
├── functional_evidence: FunctionalEvidence
├── independent_review: IndependentReviewResult | None
├── rule_promotions: list[RulePromotionProposal]
└── flags: set[EvidenceFlag]        # z.B. no_changes_detected, rule_conflict
```

---

### ViolationFinding

Einzelne gefundene Verletzung einer Architektur- oder Strukturregel.

```
ViolationFinding (frozen Pydantic model)
├── violation_type: ViolationType   # Enum: layer_violation, forbidden_dependency,
│                                   #       file_placement, naming_convention, rule_conflict
├── severity: Severity              # Enum: critical, high, medium, low (von Drift-Signalen)
├── file: str | None                # relative Dateipfad
├── line: int | None
├── rule_id: str | None             # z.B. "AVS", "PFS" oder custom rule ID
├── conflicting_rule_id: str | None # Nur bei rule_conflict
├── message: str                    # Beschreibung des Verstoßes
└── remediation: str                # Agentenverständliche Reparaturanweisung
```

---

### ActionRecommendation

Maschinenlesbares Urteil.

```
ActionRecommendation (frozen Pydantic model)
├── verdict: Verdict                # Enum: automerge, needs_fix, needs_review,
│                                   #       escalate_to_human
├── reason: str                     # Ein Satz
└── blocking_violation_count: int   # Anzahl Violations, die das Urteil erzwingen
```

**Entscheidungslogik (deterministisch):**
- `no_changes_detected` Flag gesetzt → `automerge`
- Violations mit severity `critical` oder `high` → `needs_fix`
- `rule_conflict`-Flag → `needs_review` (override)
- `independent_review_unavailable`-Flag → `needs_review` (override bei reviewpflichtigen Diffs)
- Drift Score ≤ Schwellwert AND Spec Confidence ≥ Schwellwert AND keine offenen Violations → `automerge`
- Sonst → `needs_review`

---

### FunctionalEvidence

Ergebnisse der automatischen CI-Checks.

```
FunctionalEvidence (frozen Pydantic model)
├── tests_passed: bool | None       # None = nicht verfügbar
├── tests_total: int | None
├── tests_failing: int | None
├── lint_passed: bool | None
├── typecheck_passed: bool | None
├── screenshots: list[str]          # Optionale Pfade/URLs
├── logs: list[str]                 # Optionale Log-Snippets
└── metrics: dict[str, float]       # Optionale Metriken
```

---

### IndependentReviewResult

Befunde des Reviewer-Agenten (synchron; None bei Timeout).

```
IndependentReviewResult (frozen Pydantic model)
├── available: bool                 # False wenn Timeout/Fehler
├── confidence_delta: float         # Additiver Einfluss auf spec_confidence_score
├── findings: list[str]             # Freitext-Befunde des Agents
└── spec_criteria_violated: list[str]  # Referenzierte Akzeptanzkriterien
```

---

### RulePromotionProposal

Vorschlag zur dauerhaften Regel aus wiederkehrendem Muster.

```
RulePromotionProposal (frozen Pydantic model)
├── pattern_key: str                # (violation_type, file_pattern) als String-Key
├── occurrence_count: int           # Wie oft bisher gesehen
├── threshold: int                  # Konfigurierter Schwellwert (Standard: 5)
├── suggested_rule_id: str          # Vorgeschlagene Regel-ID
├── suggested_description: str
└── affected_files: list[str]       # Dateien, in denen das Muster auftrat
```

---

### PatternHistoryEntry

Persistierter Eintrag für Rule-Promotion-Zähler (JSONL).

```
PatternHistoryEntry (TypedDict)
├── type: str           # violation_type
├── pattern: str        # file_pattern oder betroffene Datei
├── file: str
└── ts: str             # ISO timestamp
```

---

## Enumerations

```python
class ViolationType(str, Enum):
    layer_violation = "layer_violation"
    forbidden_dependency = "forbidden_dependency"
    file_placement = "file_placement"
    naming_convention = "naming_convention"
    rule_conflict = "rule_conflict"

class Verdict(str, Enum):
    automerge = "automerge"
    needs_fix = "needs_fix"
    needs_review = "needs_review"
    escalate_to_human = "escalate_to_human"

class EvidenceFlag(str, Enum):
    no_changes_detected = "no_changes_detected"
    rule_conflict = "rule_conflict"
    independent_review_unavailable = "independent_review_unavailable"
```

---

## Validation Rules

- `drift_score` ∈ [0.0, 1.0]
- `spec_confidence_score` ∈ [0.0, 1.0]
- `automerge` nur wenn `violations == []` AND `drift_score ≤ threshold` AND `spec_confidence_score ≥ threshold`
- `EvidenceFlag.no_changes_detected` → `violations` MUSS leer sein, `drift_score == 0.0`, `spec_confidence_score == 1.0`
- `ViolationType.rule_conflict` → `conflicting_rule_id` MUSS gesetzt sein

---

## Persistenz

- `.drift/pattern_history.jsonl` im Repo-Root (wird angelegt wenn nicht vorhanden)
- Kein Locking für v1 (Single-Writer-Annahme)
- Jeder `drift verify`-Aufruf appended Einträge; Read-Seite aggregiert on-the-fly
