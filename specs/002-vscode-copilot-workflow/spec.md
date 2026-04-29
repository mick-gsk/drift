# Feature Specification: VS Code Copilot Chat Workflow Integration

**Feature Branch**: `002-vscode-copilot-workflow`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "Add a spec-kit workflow integration to drift that scaffolds AI-guided analysis sessions in VS Code. When a user runs drift on their codebase, they should receive contextual follow-up actions directly in the VS Code Copilot Chat — for example a one-click button to generate a fix plan, to export findings as a report, or to start an auto-fix loop. The workflow should follow the same handoff pattern as spec-kit: each drift command completes and proposes the logical next step as a clickable prompt, so developers never lose context between analysis, review, and remediation. The integration must work without any VS Code extension or plugin install — only a prompt file and vscode-settings.json are required."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guided Fix Plan After Analysis (Priority: P1)

A developer has just run drift on their codebase and received an analysis report in the terminal. They want to act on the findings immediately without losing context or having to remember which command to run next. VS Code Copilot Chat shows a clearly labeled follow-up action labelled "Generate Fix Plan" that, when clicked, opens the drift fix-plan workflow pre-loaded with the analysis results.

**Why this priority**: This is the most common post-analysis action and directly reduces the time from "insight" to "action". Without it, developers copy-paste findings manually or forget to follow up entirely.

**Independent Test**: Can be tested by running `drift analyze` and confirming that the output includes a valid Copilot Chat prompt reference that opens the fix-plan workflow with the correct context pre-filled.

**Acceptance Scenarios**:

1. **Given** a developer has run `drift analyze` and the terminal shows findings, **When** they click the "Generate Fix Plan" prompt link in the output, **Then** VS Code Copilot Chat opens with the fix-plan workflow pre-loaded and the analysis context already populated (no re-run required).
2. **Given** a developer opens the `drift-fix-plan` prompt directly from Copilot Chat slash commands, **When** no prior analysis context is present, **Then** the prompt explains how to run drift first and offers to do so immediately.
3. **Given** a developer follows the fix-plan workflow to completion, **When** the plan is ready, **Then** the output proposes the next logical step (start auto-fix loop or export report) as a clickable action.

---

### User Story 2 - Export Findings as a Report (Priority: P2)

A developer or tech lead wants to share drift findings with their team or record them as a ticket. After seeing the analysis summary, they click "Export Report" and receive a formatted markdown document summarising the key findings, scores, and recommended actions — without writing any manual notes.

**Why this priority**: Report export serves communication and accountability needs. It is less urgent than fix plan but significantly increases the integration's value for teams.

**Independent Test**: Can be tested by triggering the export-report prompt from a prior analysis session context and confirming a structured markdown file is produced containing the findings, composite score, and per-signal breakdown.

**Acceptance Scenarios**:

1. **Given** analysis findings are available (either from a prior run or passed as context), **When** a developer triggers the "Export Report" workflow, **Then** a structured markdown report is generated listing findings, composite score, and top recommended actions.
2. **Given** the report is generated, **When** the developer reviews it, **Then** all cited findings are traceable to specific files and line ranges without ambiguity.
3. **Given** a developer triggers "Export Report" in the fix-plan workflow after completing it, **Then** the report includes both the findings and the generated fix plan as separate sections.

---

### User Story 3 - Start Auto-Fix Loop (Priority: P3)

A developer wants to automatically work through drift findings one-by-one without manually invoking each fix. They click "Start Auto-Fix Loop" from the analysis output or from the fix-plan workflow, and Copilot Chat enters a guided remediation loop — presenting each finding, suggesting a fix, confirming with the developer, and applying it before moving to the next.

**Why this priority**: The auto-fix loop provides the highest automation value but depends on the fix plan being in place first (P1). It is independently testable but builds on prior steps.

**Independent Test**: Can be tested by entering the auto-fix loop prompt with a pre-prepared findings list and confirming that exactly one finding is addressed per loop iteration, the developer is asked for confirmation before changes are applied, and the next iteration begins automatically.

**Acceptance Scenarios**:

1. **Given** a fix plan exists and a developer clicks "Start Auto-Fix Loop", **When** the loop begins, **Then** findings are presented one at a time, each with a proposed fix, and the developer is asked to confirm or skip before the next finding is processed.
2. **Given** the developer skips a finding, **When** the loop continues, **Then** the skipped finding is marked as "skipped" in a summary and the loop proceeds to the next item without re-presenting the skipped one.
3. **Given** all findings have been processed or skipped, **When** the loop completes, **Then** a summary of applied fixes and skipped items is shown, and the "Export Report" action is offered as a next step.

---

### Edge Cases

- What happens when a developer clicks a workflow prompt link but no analysis results exist in the current session context? The prompt must detect this and offer to re-run analysis first.
- How does the system handle partial analysis (e.g., only some signals ran successfully)? The workflow must clearly indicate incomplete data and not silently omit missing findings.
- What happens when a developer runs the workflow from a repository where no drift configuration exists? The prompt must guide the user to set up drift before proceeding.
- How does the workflow behave if the user's VS Code version does not support the `/` prompt command format? The prompt file must be discoverable via the Copilot Chat `@workspace` path as a fallback.
- What happens if a finding's referenced file has been deleted or moved since the analysis ran? The auto-fix loop must detect stale references and skip them with a warning rather than applying an invalid fix.
- What happens if `.vscode/drift-session.json` is older than 24 hours when a workflow prompt is opened? The prompt MUST display a staleness warning (including the session age) and recommend re-running `drift analyze`, but MUST NOT block the developer from continuing with the existing context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After each drift command that produces findings, the output MUST include a human-readable reference to the next Copilot Chat workflow step, expressed as a VS Code prompt file path or slash command that a developer can activate without typing additional arguments.
- **FR-002**: The integration MUST be deployable by placing files in `.github/prompts/` and `.vscode/settings.json` with no additional tool installation beyond a standard VS Code with GitHub Copilot. `.vscode/settings.json` MUST set `chat.promptFilesLocations` to include `.github/prompts/` so that all workflow prompts are discoverable as Copilot Chat slash commands.
- **FR-003**: At minimum three named workflow prompts MUST be provided: `drift-fix-plan`, `drift-export-report`, and `drift-auto-fix-loop`.
- **FR-004**: Each workflow prompt MUST include a structured preamble that describes its purpose, required inputs, expected outputs, and the next logical step it hands off to.
- **FR-005**: The `drift-fix-plan` prompt MUST accept analysis context (composite score, top findings, repo path) passed through the chat session without requiring the developer to re-run `drift analyze`.
- **FR-006**: The `drift-export-report` prompt MUST produce a self-contained markdown document that does not require further tool access to read or share.
- **FR-007**: The `drift-auto-fix-loop` prompt MUST process findings one at a time, require explicit developer confirmation before applying any change, and maintain a running summary of applied and skipped items.
- **FR-008**: Each prompt MUST end with a proposal for the next logical workflow step, referencing the exact prompt name the developer should activate next.
- **FR-009**: The `drift analyze` output (both Rich terminal and JSON) MUST include a clearly delimited HandoffBlock listing available Copilot Chat next-step prompts and the top 5 findings by severity, so the link between CLI output and Chat workflow is explicit without overwhelming the terminal.
- **FR-010**: Workflow prompts MUST gracefully handle missing analysis context by detecting its absence and offering to invoke `drift analyze` as a recovery step.

### Key Entities

- **WorkflowPrompt**: A `.prompt.md` file under `.github/prompts/` that encapsulates one step in the guided analysis-to-remediation workflow, including its purpose, inputs, outputs, and handoff reference.
- **AnalysisContext** (implemented as `SessionData` in `src/drift/copilot_handoff/_models.py`): The subset of drift analysis results (composite score, top-N findings by severity, repo path, analysis timestamp) that is passed between workflow steps to preserve continuity. AnalysisContext is persisted to `.vscode/drift-session.json` after each analysis run; workflow prompts read this file on entry so the developer can re-enter any step after closing the Copilot Chat session without re-running `drift analyze`. The session file is written only when `drift analyze` runs without an explicit `--output` file redirect. If the file is older than 24 hours, the prompt shows a staleness warning and recommends re-analysis but does not block continuation.
- **HandoffBlock**: A standardised output block appended to drift CLI output that lists the next available Copilot Chat actions as prompt references and the top 5 findings by severity, allowing one-click transitions. The full findings list is available in `.vscode/drift-session.json`.
- **WorkflowSession**: The logical sequence of prompts a developer moves through during one analysis-to-remediation cycle (analyze → fix-plan → auto-fix-loop or export-report).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer who has never used the workflow integration can reach an actionable fix plan within 2 steps after running `drift analyze` — no documentation lookup required.
- **SC-002**: Zero additional software installations are required beyond a standard repository checkout and VS Code with GitHub Copilot Chat.
- **SC-003**: All three workflow prompts (`drift-fix-plan`, `drift-export-report`, `drift-auto-fix-loop`) are reachable from a single `drift analyze` output without navigating away from the terminal or Copilot Chat window.
- **SC-004**: Analysis context (findings, composite score, affected file paths) is available in every subsequent workflow step without the developer manually copying data between windows.
- **SC-005**: A developer who skips or closes a workflow prompt mid-session can re-enter the same step via the Copilot Chat slash command and resume with the same context — no repeated analysis run needed. The context is read from `.vscode/drift-session.json`, which is written after every `drift analyze` run and updated after each workflow step.
- **SC-006**: The export-report workflow produces a markdown file that is readable and useful to a non-technical stakeholder without any drift-specific knowledge.

## Assumptions

- Developers have VS Code with the GitHub Copilot Chat extension installed; no additional drift-specific extension is assumed.
- The `.github/prompts/` directory convention used by spec-kit is already known and trusted in the target workspace.
- Drift's existing `.github/prompts/` files (e.g., `drift-fix-loop.prompt.md`) serve as the implementation pattern; the new prompts extend rather than replace them.
- The VS Code Copilot Chat slash command mechanism (`/command-name`) is stable enough to depend on for the one-click handoff experience; it requires `chat.promptFilesLocations` in `.vscode/settings.json` to point at `.github/prompts/`.
- Mobile and browser-based VS Code variants are out of scope for v1; the integration targets desktop VS Code only.
- The `drift analyze` CLI output format (Rich terminal + JSON) can be extended with a handoff block without breaking existing consumers, as the block is appended after the current output boundary.
- `.vscode/drift-session.json` is a local-only, workspace-scoped file (added to `.gitignore` and never committed); it contains no secrets or credentials, only analysis metadata (file paths, scores, finding summaries).

## Clarifications

### Session 2026-04-27

- Q: How should AnalysisContext survive a VS Code Copilot Chat session close? → A: Persisted to `.vscode/drift-session.json` — prompts read this file on entry; survives restarts.
- Q: How many findings should the HandoffBlock reference in the terminal output? → A: Top 5 by severity — full findings list remains available in `.vscode/drift-session.json`.
- Q: Should `.vscode/drift-session.json` be committable for team sharing? → A: Always in `.gitignore`; never committed — local session state only; team sharing is done via the exported report (FR-006).
- Q: If `.vscode/drift-session.json` is older than 24 hours, should the workflow prompt block continuation? → A: Warn but continue — show session age, recommend re-analysis, but do not block the developer.
