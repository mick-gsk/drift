# Drift — Developer Task Runner
# Usage: make help
#
# On Windows: use via Git Bash, WSL, or install GNU Make.
# All targets mirror the pre-push hook / CI pipeline steps.

.DEFAULT_GOAL := help

PYTHON   ?= python
PYTEST   ?= pytest
RUFF     ?= ruff
MYPY     ?= $(PYTHON) -m mypy

SRC      := packages/
SRC_LEGACY := src/
TESTS    := tests/

.PHONY: help install lint lint-fix typecheck test test-fast test-dev test-lf test-contract smoke-pr smoke-nightly test-all coverage check self ci preflight feat-start fix-start catalog gate-check task-card feat-bundle handover changelog-entry changelog-insert audit-diff agent-harness-check repro-bundle markdown-lint package-kpis-github-usage package-kpis-downloads package-kpis-real-public package-kpis-example quality-score clean guard-refresh test-for replay-benchmark repair-eval ab-harness kpi-update kpi-report eval-all

help:  ## Show all available commands
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Dev install (editable + all dev extras) and activate git hooks
	pip install -e ".[dev]"
	git config core.hooksPath .githooks
	@command -v pre-commit >/dev/null 2>&1 && pre-commit install --install-hooks || echo "  (pre-commit not found — skipping hook install)"

lint:  ## Run ruff linter (packages/ + tests/ - matches CI)
	$(RUFF) check $(SRC) $(TESTS)

lint-fix:  ## Run ruff with auto-fix
	$(RUFF) check --fix $(SRC) $(TESTS)

typecheck:  ## Run mypy type checker (packages - matches CI)
	$(MYPY) packages/drift/src/drift packages/drift-engine/src/drift_engine packages/drift-sdk/src/drift_sdk packages/drift-output/src/drift_output packages/drift-cli/src/drift_cli packages/drift-mcp/src/drift_mcp packages/drift-session/src/drift_session packages/drift-config/src/drift_config

test:  ## Run tests in parallel (skip slow smoke tests)
	$(PYTEST) -v --tb=short --ignore=tests/test_smoke_real_repos.py -n auto --dist=loadscope

test-fast:  ## Fast unit tests — parallel, skip slow tests, stop on first failure
	$(PYTEST) -v --tb=short -m "not slow" -x --ignore=tests/test_smoke_real_repos.py -n auto --dist=loadscope

test-dev:  ## Local dev loop — skip slow/performance/ground-truth tests
	$(PYTEST) -q --tb=short -m "not slow and not performance and not ground_truth" --ignore=tests/test_smoke_real_repos.py --maxfail=1 -n auto --dist=loadscope

test-lf:  ## Local dev loop — rerun last failed, with fast-marker filter
	$(PYTEST) -q --tb=short --lf -m "not slow and not performance and not ground_truth" --ignore=tests/test_smoke_real_repos.py --maxfail=1 -n auto --dist=loadscope

test-contract:  ## SARIF/JSON contract tests only
	$(PYTEST) -v --tb=short -m contract

smoke-pr:  ## Fast smoke tests on representative external repos (cached)
	$(PYTEST) tests/test_smoke_real_repos.py -v --run-slow --smoke-profile=pr

smoke-nightly:  ## Full smoke matrix on all external repos (cached)
	$(PYTEST) tests/test_smoke_real_repos.py -v --run-slow --smoke-profile=nightly

test-all:  ## All tests including slow smoke tests
	$(PYTEST) -v --tb=short --run-slow --smoke-profile=nightly

coverage:  ## Tests with coverage report (quick, skips slow tests)
	$(PYTEST) -q --tb=short --cov=drift --ignore=tests/test_smoke_real_repos.py -p no:xdist

check:  ## Run all checks: lint + typecheck + tests (incl. slow) + self-analysis
	@echo ">>> [1/4] Lint..."
	@$(MAKE) --no-print-directory lint
	@echo ">>> [2/4] Type check..."
	@$(MAKE) --no-print-directory typecheck
	@echo ">>> [3/4] Tests + coverage (incl. slow)..."
	@$(PYTEST) -q --tb=short --cov=drift --ignore=tests/test_smoke_real_repos.py --run-slow -p no:xdist
	@echo ">>> [4/4] Self-analysis..."
	@$(MAKE) --no-print-directory self
	@git rev-parse HEAD 2>/dev/null > .git/.drift-prepush-last-success || true
	@echo ">>> All checks passed. Pre-push cache written — next git push will skip expensive CI."

markdown-lint:  ## Lint Markdown docs
	npx markdownlint-cli2

self:  ## Drift self-analysis
	drift analyze --repo . --format json > /dev/null

package-kpis-github-usage:  ## Derive usage events from public GitHub dependency declarations
	$(PYTHON) scripts/fetch_github_usage.py \
		--package drift-analyzer \
		--max-pages 5 \
		--output benchmark_results/package_kpis/github_usage_events.csv

package-kpis-downloads:  ## Fetch real monthly PyPI downloads to CSV
	$(PYTHON) scripts/fetch_pypistats.py \
		--package drift-analyzer \
		--months 12 \
		--output benchmark_results/package_kpis/pypi_downloads_monthly.csv

package-kpis-real-public:  ## Build KPI report from public GitHub usage + PyPI downloads
	$(MAKE) --no-print-directory package-kpis-github-usage
	$(MAKE) --no-print-directory package-kpis-downloads
	$(PYTHON) scripts/package_kpis.py \
		--package drift-analyzer \
		--usage-csv benchmark_results/package_kpis/github_usage_events.csv \
		--downloads-csv benchmark_results/package_kpis/pypi_downloads_monthly.csv \
		--thresholds-json examples/package-kpis/kpi-thresholds.json \
		--months 12 \
		--output benchmark_results/package_kpis/package_kpis_real.json

package-kpis-example:  ## Generate monthly package KPI example report JSON
	$(PYTHON) scripts/package_kpis.py \
		--package drift-analyzer \
		--usage-csv examples/package-kpis/usage.csv \
		--defects-csv examples/package-kpis/defects.csv \
		--currency-versions 1.4.1,1.4.0 \
		--thresholds-json examples/package-kpis/kpi-thresholds.json \
		--months 12 \
		--output benchmark_results/package_kpis_example.json

quality-score:  ## Build ISO/IEC 25010 quality scorecard JSON
	$(PYTHON) scripts/quality_scorecard.py --apply

preflight:  ## [Agent] Run ALL PR-blocking CI checks locally before committing (use this, not make ci)
	$(PYTHON) scripts/agent_preflight.py $(ARGS)

ci:  ## Replicate full CI pipeline locally (exact CI parity: packages/ lint, packages mypy, pytest not-slow)
	@echo ">>> [ci/1] Version check..."
	$(PYTHON) scripts/check_version.py --check-semver
	@echo ">>> [ci/2] Lint (packages/ tests/ - same paths as CI)..."
	$(RUFF) check packages/ $(TESTS)
	@echo ">>> [ci/3] Type-check (packages - same target as CI)..."
	$(MYPY) packages/drift/src/drift packages/drift-engine/src/drift_engine packages/drift-sdk/src/drift_sdk packages/drift-output/src/drift_output packages/drift-cli/src/drift_cli packages/drift-mcp/src/drift_mcp packages/drift-session/src/drift_session packages/drift-config/src/drift_config
	@echo ">>> [ci/4] Tests (not slow - same marker as CI)..."
	$(PYTEST) -q --tb=short -m "not slow" --ignore=tests/test_smoke_real_repos.py
	@echo ">>> [ci/5] Self-analysis..."
	$(MAKE) --no-print-directory self
	@echo ">>> CI-parity check complete. Safe to push."

# ---------------------------------------------------------------------------
# Agent Workflow Shortcuts
# ---------------------------------------------------------------------------

feat-start:  ## [Agent] Start feat workflow: show required steps and active gates
	@echo "=== feat workflow - active gates: 2 + 3 + 6 + 8 ==="
	@echo ""
	@echo "  1. tests/            - Add or update tests (Gate 2 condition 1)"
	@echo "  2. src/drift/        - Implement feature code"
	@echo "  3. benchmark_results - Generate evidence (Gate 2 condition 2+3):"
	@echo "     python scripts/generate_feature_evidence.py --version X.Y.Z --slug <slug>"
	@echo "  4. CHANGELOG.md      - Add entry (Gate 3)"
	@echo "  5. docs/STUDY.md     - Update study notes (Gate 2 condition 4)"
	@echo "  6. make check        - Run full local CI checks (Gate 8)"

fix-start:  ## [Agent] Start fix workflow: show required steps and active gates
	@echo "=== fix workflow - active gates: 3 + 8 ==="
	@echo ""
	@echo "  1. tests/            - Add a failing test for the bug"
	@echo "  2. src/drift/        - Implement minimal fix"
	@echo "  3. CHANGELOG.md      - Add entry (Gate 3)"
	@echo "  4. make test-fast    - Run quick verification (Gate 8)"

catalog:  ## [Agent] List scripts with short descriptions (use ARGS='--search keyword')
	$(PYTHON) scripts/catalog.py $(ARGS)

gate-check:  ## [Agent] Proactive gate status before commit/push (COMMIT_TYPE=feat|fix|chore|signal)
	$(PYTHON) scripts/gate_check.py --commit-type $(COMMIT_TYPE)

task-card:  ## [Agent] Render compact kickoff card (TYPE=feat|fix|chore|signal|prompt|review TASK='short description')
	$(if $(strip $(TYPE)),,$(error TYPE missing. Use: make task-card TYPE=fix TASK='...'))
	$(if $(strip $(TASK)),,$(error TASK missing. Use: make task-card TYPE=fix TASK='...'))
	$(PYTHON) scripts/task_card.py --type $(TYPE) --task "$(TASK)"

feat-bundle:  ## [Agent] Generate + validate feature evidence, then auto-update CHANGELOG and STUDY.md (VERSION=X.Y.Z SLUG=name [MSG='description'])
	@[ "$(VERSION)" ] || (echo "Error: VERSION missing. Use: make feat-bundle VERSION=X.Y.Z SLUG=name"; exit 1)
	@[ "$(SLUG)" ] || (echo "Error: SLUG missing. Use: make feat-bundle VERSION=X.Y.Z SLUG=name"; exit 1)
	@echo ">>> [1/3] Generate feature evidence..."
	$(PYTHON) scripts/generate_feature_evidence.py --version $(VERSION) --slug $(SLUG)
	@echo ">>> [2/3] Validate generated evidence..."
	$(PYTHON) scripts/validate_feature_evidence.py benchmark_results/v$(VERSION)_$(SLUG)_feature_evidence.json --require-generated-by --push-head HEAD
	@echo ">>> [3/3] Auto-update CHANGELOG.md and docs/STUDY.md..."
	$(PYTHON) scripts/feat_bundle_followup.py benchmark_results/v$(VERSION)_$(SLUG)_feature_evidence.json $(if $(MSG),--msg "$(MSG)",)

handover:  ## [Agent] Generate session handover artifact (TASK='description')
	@[ "$(TASK)" ] || (echo "Error: TASK missing. Use: make handover TASK='description'"; exit 1)
	$(PYTHON) scripts/session_handover.py --task "$(TASK)"
	$(PYTHON) scripts/update_work_artifacts_index.py

update-artifacts-index:  ## [Agent] Regenerate work_artifacts/index.json (run after any session)
	$(PYTHON) scripts/update_work_artifacts_index.py

changelog-entry:  ## [Agent] Preview changelog snippet on stdout (COMMIT_TYPE=feat|fix|chore MSG='text')
	@[ "$(COMMIT_TYPE)" ] || (echo "Error: COMMIT_TYPE missing."; exit 1)
	@[ "$(MSG)" ] || (echo "Error: MSG missing."; exit 1)
	$(PYTHON) scripts/generate_changelog_entry.py --commit-type $(COMMIT_TYPE) --message "$(MSG)"

changelog-insert:  ## [Agent] Insert changelog entry into CHANGELOG.md in-place (COMMIT_TYPE=feat|fix|chore MSG='text')
	@[ "$(COMMIT_TYPE)" ] || (echo "Error: COMMIT_TYPE missing."; exit 1)
	@[ "$(MSG)" ] || (echo "Error: MSG missing."; exit 1)
	$(PYTHON) scripts/integrate_changelog_entry.py --commit-type $(COMMIT_TYPE) --message "$(MSG)"

audit-diff:  ## [Agent] Show required risk-audit updates for current diff
	$(PYTHON) scripts/risk_audit_diff.py

agent-harness-check:  ## [Agent] Validate harness navigation, audit docs, and MCP boundaries
	$(PYTHON) scripts/check_agent_harness_contract.py --root .

repro-bundle:  ## [Agent] Create a compact repro bundle for a failed agent turn (SUMMARY, FAILURE, CHECK, ENTRYPOINT required)
	@[ "$(SUMMARY)" ] || (echo "Error: SUMMARY missing. Use: make repro-bundle SUMMARY='...' FAILURE='...' CHECK='...' ENTRYPOINT='...'"; exit 1)
	@[ "$(FAILURE)" ] || (echo "Error: FAILURE missing."; exit 1)
	@[ "$(CHECK)" ] || (echo "Error: CHECK missing."; exit 1)
	@[ "$(ENTRYPOINT)" ] || (echo "Error: ENTRYPOINT missing."; exit 1)
	$(PYTHON) scripts/agent_repro_bundle.py \
		--summary "$(SUMMARY)" \
		--failure-context "$(FAILURE)" \
		--last-check-status "$(CHECK)" \
		$(if $(NUDGE),--last-nudge-status "$(NUDGE)",) \
		--next-agent-entrypoint "$(ENTRYPOINT)" \
		$(if $(SESSION_ID),--session-id "$(SESSION_ID)",)

clean:  ## Remove caches and build artifacts
	rm -rf .drift-cache .pytest_cache .ruff_cache .mypy_cache htmlcov dist build
	rm -f .coverage out.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

guard-refresh:  ## Regenerate guard SKILL.md files from latest ArchGraph (runs drift map first)
	$(PYTHON) -m drift map --repo . --exit-zero
	$(PYTHON) -m drift generate-skills --repo . --write --force
	@echo "Guard skills refreshed. Review changes before committing."

test-for:  ## Run tests relevant for a specific source file: make test-for FILE=src/drift/session.py
	$(PYTHON) scripts/_test_map_lookup.py $(FILE)

# ---------------------------------------------------------------------------
# Internal Evaluation System
# ---------------------------------------------------------------------------

replay-benchmark:  ## Baustein 1: Historical replay benchmark (dry-run)
	$(PYTHON) scripts/replay_benchmark.py --dry-run run

repair-eval:  ## Baustein 2: Repair evaluation with side-effect tracking
	$(PYTHON) scripts/repair_eval.py run --apply

ab-harness:  ## Baustein 3: A/B harness (mock mode, deterministic)
	$(PYTHON) scripts/ab_harness.py run --mock-mode neutral
	$(PYTHON) scripts/ab_harness.py stats
	$(PYTHON) scripts/ab_harness.py report

kpi-update:  ## Baustein 4: Capture KPI snapshot
	$(PYTHON) scripts/kpi_trend_update.py --apply

kpi-report:  ## Baustein 4: Generate weekly KPI report
	$(PYTHON) scripts/kpi_weekly_report.py --apply

eval-all:  ## Run all internal evaluation building blocks
	@echo ">>> [1/4] Replay Benchmark..."
	@$(MAKE) --no-print-directory replay-benchmark
	@echo ">>> [2/4] Repair Evaluation..."
	@$(MAKE) --no-print-directory repair-eval
	@echo ">>> [3/4] A/B Harness..."
	@$(MAKE) --no-print-directory ab-harness
	@echo ">>> [4/4] KPI Update..."
	@$(MAKE) --no-print-directory kpi-update
	@$(MAKE) --no-print-directory kpi-report
	@echo ">>> All evaluation building blocks completed."
