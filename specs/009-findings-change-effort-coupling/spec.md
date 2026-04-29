# Feature Specification: Findings Coupled to Change Effort and Responsibility Boundaries

**Feature Branch**: `009-findings-change-effort-coupling`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: User description: "Befunde stärker an Änderungsaufwand und Verantwortungsgrenzen koppeln"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Boundary-Aware Finding Review (Priority: P1)

A developer receives drift findings after a scan. Each finding immediately tells them which architectural responsibility boundary is blurred or crossed — without the developer needing to trace the code themselves or understand the signal logic.

**Why this priority**: This is the core ask from POLICY#S1.p3: findings must be actionable. A finding that names a pattern but not the violated boundary forces the developer to interpret the finding themselves, reducing actionability.

**Independent Test**: A developer with no prior knowledge of the scanned repo can read a finding and answer "which responsibility boundary is violated here?" correctly — based solely on the finding text.

**Acceptance Scenarios**:

1. **Given** a finding for a signal that detects cross-boundary coupling, **When** the developer reads the `reason` field, **Then** the text explicitly names the responsibility boundary that is blurred or crossed (e.g., "data access mixed with presentation logic", "orchestration logic inside a utility module").
2. **Given** a finding where multiple signals fire on the same location, **When** the developer reads each finding, **Then** each finding names a distinct responsibility boundary relevant to its own signal — not a generic description.
3. **Given** a finding on a file that has no obvious boundary violation (purely structural smell), **When** the developer reads the `reason` field, **Then** the text still connects to the expected responsibility of the containing module or layer.

---

### User Story 2 - Change-Cost Transparency in next_action (Priority: P2)

A developer planning a refactor reads `next_action` texts and understands, for each finding, what kind of follow-up change becomes harder or more expensive if the finding is ignored.

**Why this priority**: Knowing that a boundary is crossed is not enough. Knowing *which type of change will be expensive* helps developers prioritize — and justifies the finding's priority to team leads and maintainers.

**Independent Test**: A developer can answer "what specific category of change is made harder by this finding?" solely from the `next_action` text of a P1 finding.

**Acceptance Scenarios**:

1. **Given** a finding with a `next_action`, **When** the developer reads it, **Then** the text names a concrete category of change that will be more expensive or risky if the finding is not resolved (e.g., "Extracting this into a separate service will require splitting this file", "Adding a new data model variant will require coordinated changes across all callers").
2. **Given** a finding that was previously `next_action: "Refactor toward single responsibility"`, **When** the updated text is read, **Then** it names at least one concrete change type that becomes difficult — not just "refactor".
3. **Given** a finding in a critical architectural location (e.g., an ingestion boundary), **When** the `next_action` text is read, **Then** it identifies the specific change category (feature extension, interface change, extraction) that is risky.

---

### User Story 3 - Consistent Boundary Language Across Findings (Priority: P3)

A team lead reviewing multiple findings across a codebase can compare responsibility-boundary language across different signals and quickly identify which architectural areas have the most mixed responsibilities — without normalizing the text manually.

**Why this priority**: Consistent boundary vocabulary across signals makes findings comparable and aggregatable. Without consistency, users must map each signal's language to their own mental model.

**Independent Test**: After scanning a repo, a user can sort or group findings by boundary type using only the `reason` text.

**Acceptance Scenarios**:

1. **Given** findings from two different signals that both detect boundary violations in the same layer (e.g., both in the data layer), **When** the `reason` texts are compared, **Then** they use compatible boundary terminology — not two unrelated framings.
2. **Given** a finding where the boundary terminology has been updated, **When** the full scan output is reviewed, **Then** no finding for that signal type still uses the previous vague pattern-only language.

---

### Edge Cases

- What happens when a signal fires on a file that deliberately mixes responsibilities by design (e.g., a facade)? → The finding must still name the trade-off, not suppress the boundary description.
- What happens when a signal detects a violation that spans more than two responsibility layers? → The `reason` field names the primary violated boundary; a secondary boundary may be mentioned but is not required.
- What happens when a `next_action` already contained a specific change reference? → It is kept; enrichment is additive, not a replacement that removes existing specifics.
- How does the system handle signals with `severity: info` where change cost may be low? → Even info-level findings must name the boundary, but change-cost language may be lighter ("may complicate" vs. "will require").

## Clarifications

### Session 2026-04-29

- Q: Welche Signale sind Pflicht-Ziel für das Update (Signal-Scope)? → A: Nur explizit benannte Signale (PFS, AVS, MDS, EDS) sind Pflicht; alle anderen optional
- Q: Welche Ausgabeformate müssen aktualisiert werden (Output-Scope)? → A: Alle Formate (Rich, JSON, SARIF) übernehmen die aktualisierten Strings automatisch — kein Format-spezifischer Scope
- Q: Wer legt Boundary-Terminologie fest (Vokabular-Governance)? → A: Empfohlenes Kurz-Vokabular im bestehenden `drift-finding-message-authoring/SKILL.md` als Orientierung — kein Merge-Gate
- Q: Wann gilt ein `reason`-Text als „pattern-only" und damit als Pflicht-Update-Kandidat? → A: Text nennt weder einen konkreten Layer/Concern noch eine Änderungsimplikation — beide Kriterien müssen fehlen
- Q: Wie werden die aktualisierten `reason`/`next_action`-Texte verifiziert (Testabsicherung)? → A: Smoke-Check — Assertion dass mind. ein Layer/Concern-Keyword im `reason`-Text vorhanden ist (enthält-Prüfung, keine Exakt-Übereinstimmung)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each finding's `reason` field MUST name the specific responsibility boundary that the signal considers violated or blurred — using a concrete description visible without tracing the code.
- **FR-002**: Each finding's `next_action` field MUST include a reference to at least one concrete category of follow-up change that becomes harder or more expensive if the finding is not addressed.
- **FR-003**: Boundary descriptions in `reason` fields MUST be specific to the module or layer context in which the finding occurs — not a generic reformulation of the signal name.
- **FR-004**: Change-cost language in `next_action` MUST distinguish between different effort levels: changes that are merely inconvenienced vs. changes that require cross-cutting coordination.
- **FR-005**: The enriched finding texts MUST remain factual and directly derivable from what the signal detected — no speculative descriptions that the signal cannot support.
- **FR-006**: The signals PFS (Pattern Fragmentation Score), AVS (Abstraction Violation Score), MDS (Module Dependency Score), and EDS (Entanglement Depth Score) MUST be updated with boundary and change-cost language; all other signals are optional candidates that MAY be updated but are not required for acceptance.
- **FR-007**: The `reason` and `next_action` text changes MUST NOT alter the signal's detection logic, scoring weights, or any structured output field beyond the string content of those two fields.

### Key Entities

- **Finding**: A single signal result attached to a file location, carrying `reason` (why this is a problem) and `next_action` (what to do about it) string fields.
- **Responsibility Boundary**: An architectural demarcation between concerns or layers (e.g., data access vs. business logic, orchestration vs. computation, presentation vs. domain).
- **Change Category**: A named type of follow-up change whose cost is affected by the finding (e.g., "interface extraction", "service split", "data model migration", "feature extension").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer unfamiliar with a scanned codebase can correctly identify the violated responsibility boundary from a finding's `reason` text within 30 seconds, without consulting any other source.
- **SC-002**: For every finding with severity `warning` or `error`, the `next_action` text names at least one concrete change category that is made harder — not just a generic refactoring directive.
- **SC-003**: After the update, no finding for the targeted signals (PFS, AVS, MDS, EDS) qualifies as "pattern-only" — defined as: the `reason` text names neither a concrete layer/concern nor a change implication. Both criteria must be absent for a text to require update; presence of either one is sufficient to be exempt.
- **SC-004**: The precision and recall scores of affected signals remain unchanged after the text enrichment — finding text updates do not alter detection behavior.
- **SC-005**: For each mandatory signal (PFS, AVS, MDS, EDS), an automated test asserts that the `reason` text of at least one representative finding contains a keyword from a defined layer/concern reference list — verified via substring match, not exact-string comparison.

## Assumptions

- This feature improves text content in existing `reason` and `next_action` fields only; no new structured fields are added as part of this feature.
- The primary targets are signals whose findings currently describe patterns without naming responsibility boundaries or change implications; signals with already-specific language are excluded.
- "Responsibility boundary" is understood in the classic layered-architecture sense (presentation, domain, data access, infrastructure, orchestration) — domain-specific refinements are in scope for individual signal authors.
- Boundary vocabulary consistency is governed by a recommended short-list added to the existing `.github/skills/drift-finding-message-authoring/SKILL.md`; no new vocabulary file is created and no merge gate enforces adherence.
- Change-cost language does not require dynamic analysis of the codebase; it is expressed as a typical pattern ("in most codebases, this pattern makes X harder") rather than a per-repo calculation.
- A `reason` text is classified as "pattern-only" (mandatory update target) only when it names neither a concrete layer/concern nor a change implication; a text satisfying either criterion is exempt from mandatory update.- Test verification of updated texts uses keyword smoke-checks (substring/contains assertions against a small reference list of layer/concern terms) rather than exact-string matches, to avoid coupling tests to incidental phrasing.- The update scope covers `reason` and `next_action` strings in signal source files; documentation and test fixture strings are updated as a consequence, not as a separate scope.
- All output formats (Rich CLI, JSON, SARIF) render `reason` and `next_action` from the same Finding model string fields and therefore inherit updated texts automatically — no format-specific output work is in scope.
