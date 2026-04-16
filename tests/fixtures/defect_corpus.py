"""External-ground-truth Defect Corpus for drift.

Each entry wraps a :class:`GroundTruthFixture` with provenance metadata that
links the synthetic code back to a publicly confirmed bug or bug class.

Design constraints
------------------
* **Transformative reproduction only.**  No entry contains verbatim original
  source code.  Function names, variable names, and structural layouts are
  independently rewritten to express the same bug *class*, not the same bug.
* **Recall-only.**  The corpus measures recall (can drift detect known bad
  patterns?), not precision.  Each fixture therefore contains only
  ``should_detect=True`` expectations.
* **External ground truth.**  The ``evidence_url`` field links to a
  third-party source (GitHub issue, CVE, commit) that confirms the pattern
  as a real defect.

Usage
-----
Import ``ALL_DEFECT_CORPUS`` and pass entries to the precision engine::

    from tests.fixtures.defect_corpus import ALL_DEFECT_CORPUS
    from drift.precision import run_fixture, has_matching_finding

    for entry in ALL_DEFECT_CORPUS:
        findings, _ = run_fixture(entry.fixture, tmp_path)
        detected = has_matching_finding(findings, entry.fixture.expected[0])
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from drift.models import SignalType
from tests.fixtures.ground_truth import ExpectedFinding, FixtureKind, GroundTruthFixture


class BugClass(enum.StrEnum):
    """High-level classification of a defect entry."""

    SECURITY = "security"
    ARCHITECTURAL = "architectural"
    QUALITY = "quality"
    LOGIC = "logic"


@dataclass
class DefectCorpusEntry:
    """A single entry in the external-ground-truth defect corpus.

    Fields
    ------
    fixture : GroundTruthFixture
        The synthetic codebase that reproduces the bug class.
    evidence_url : str
        Canonical external source confirming the bug (GitHub issue, CVE, etc.).
    bug_summary : str
        One sentence describing the real-world bug that inspired this entry.
    bug_class : BugClass
        High-level category.
    inspired_by_note : str
        Human-readable disclaimer clarifying the transformative nature of the entry.
    pre_fix_note : str
        What was wrong in the pre-fix state (i.e. in ``fixture.files``).
    """

    fixture: GroundTruthFixture
    evidence_url: str
    bug_summary: str
    bug_class: BugClass
    inspired_by_note: str
    pre_fix_note: str
    tags: list[str] = field(default_factory=list)


# ── dc_001: Circular Import (CIR) ────────────────────────────────────────────
#
# Pattern class: Module A imports from Module B at import time; Module B
# imports from Module A at import time.  This causes ImportError or partially
# initialised modules in production.  Confirmed class; circular-import bugs
# are catalogued in CPython issue tracker and many popular frameworks.
#
# Evidence: https://github.com/pallets/flask/issues/2735
#           https://docs.python.org/3/faq/programming.html#what-are-the-best-practices-for-using-import-in-a-module

DC_001_CIRCULAR_IMPORT = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_001_circular_import",
        description="dc_001 — Module A and Module B mutually import each other at the top level, causing circular-import failures.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "app/__init__.py": "",
            "app/services.py": (
                "from app.models import UserRecord\n"
                "\n"
                "\ndef get_user(user_id: int) -> 'UserRecord':\n"
                "    return UserRecord(user_id)\n"
            ),
            "app/models.py": (
                "from app.services import get_user\n"
                "\n"
                "\nclass UserRecord:\n"
                "    def __init__(self, user_id: int) -> None:\n"
                "        self.user_id = user_id\n"
                "        self._resolved = get_user  # type: ignore[assignment]\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.CIRCULAR_IMPORT,
                file_path="app/services.py",
                should_detect=True,
                description="Circular import between services.py and models.py",
            ),
        ],
    ),
    evidence_url="https://github.com/pallets/flask/issues/2735",
    bug_summary=(
        "Flask circular-import pattern: app module imports from models, models imports "
        "from app — causes ImportError or partially-initialised name at startup."
    ),
    bug_class=BugClass.ARCHITECTURAL,
    inspired_by_note=(
        "Transformative reproduction of the circular-import bug class documented in "
        "Flask issue #2735 and the Python FAQ.  All names are original."
    ),
    pre_fix_note=(
        "app/models.py imports get_user from app/services.py while app/services.py "
        "imports UserRecord from app/models.py — mutual top-level dependency cycle."
    ),
    tags=["circular_import", "startup_failure", "python"],
)

# ── dc_002: Broad Exception Monoculture (BEM) ────────────────────────────────
#
# Pattern class: Every error handler in a module uses `except Exception: pass`
# or `except Exception: return None`, silently swallowing failures.  When a
# genuine error occurs (network timeout, invalid input, auth failure), it is
# dropped without logging, tracing, or re-raising.
#
# Evidence: https://github.com/psf/requests/issues/3142 (silent exception in
#           retry logic); OWASP Top 10 A09 Security Logging and Monitoring
#           Failures; PEP 8 "bare except" section.

DC_002_BROAD_EXCEPTION_MONOCULTURE = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_002_broad_exception_monoculture",
        description="dc_002 — All three handlers in the same module use except Exception swallowing (pass or log-only), preventing any error from surfacing.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "handlers/__init__.py": "",
            "handlers/auth.py": (
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\ndef validate_token(token: str) -> bool:\n"
                "    try:\n"
                "        _decode(token)\n"
                "        return True\n"
                "    except Exception:\n"
                "        pass\n"
                "\n"
                "\ndef _decode(token: str) -> dict:\n"
                "    import json\n"
                "    return json.loads(token)\n"
            ),
            "handlers/payments.py": (
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\ndef charge_card(amount: float, card_id: str) -> None:\n"
                "    try:\n"
                "        _gateway_call(amount, card_id)\n"
                "    except Exception:\n"
                "        pass\n"
                "\n"
                "\ndef refund_card(amount: float, card_id: str) -> None:\n"
                "    try:\n"
                "        _gateway_call(-amount, card_id)\n"
                "    except Exception:\n"
                "        pass\n"
                "\n"
                "\ndef _gateway_call(amount: float, card_id: str) -> None:\n"
                "    raise NotImplementedError\n"
            ),
            "handlers/data.py": (
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\ndef load_record(record_id: int) -> None:\n"
                "    try:\n"
                "        _fetch(record_id)\n"
                "    except Exception:\n"
                "        pass\n"
                "\n"
                "\ndef _fetch(record_id: int) -> None:\n"
                "    raise RuntimeError('db unavailable')\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE,
                file_path="handlers/",
                should_detect=True,
                description="All handlers use except Exception with silent pass — no re-raise, no logging",  # noqa: E501
            ),
        ],
    ),
    evidence_url="https://github.com/psf/requests/issues/3142",
    bug_summary=(
        "Silent exception swallowing in all error handlers — every except clause "
        "silently passes without logging or re-raising, hiding real failures."
    ),
    bug_class=BugClass.QUALITY,
    inspired_by_note=(
        "Transformative reproduction of the broad-exception-monoculture pattern "
        "catalogued in psf/requests issue #3142 and OWASP A09.  All names original."
    ),
    pre_fix_note=(
        "handlers/auth.py, handlers/payments.py, and handlers/data.py each catch "
        "Exception and silently pass — four total handlers, all swallowing."
    ),
    tags=["broad_exception", "silent_failure", "observability"],
)

# ── dc_003: Mutant Duplicate (MDS) ───────────────────────────────────────────
#
# Pattern class: A validation or sanitisation function is copy-pasted across
# service modules.  One copy receives a security fix (e.g., length cap, allow-
# list); the other copy is not updated.  The stale copy becomes a vulnerability.
#
# Evidence: Copy-paste bug class documented in
#   https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-7529 (nginx range
#   filter copy-paste overflow); numerous Python projects.

DC_003_MUTANT_DUPLICATE = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_003_mutant_duplicate",
        description="dc_003 — sanitize_payload is copy-pasted verbatim in two service modules; the stale copy will diverge when the original is patched.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "svc/__init__.py": "",
            "svc/registration.py": (
                "def sanitize_payload(data: dict) -> dict:\n"
                "    \"\"\"Strip whitespace and lower-case string values.\"\"\"\n"
                "    result = {}\n"
                "    for key, value in data.items():\n"
                "        if isinstance(value, str):\n"
                "            result[key] = value.strip().lower()\n"
                "        elif isinstance(value, list):\n"
                "            result[key] = [v.strip() if isinstance(v, str) else v for v in value]\n"  # noqa: E501
                "        else:\n"
                "            result[key] = value\n"
                "    return result\n"
            ),
            "svc/profile_edit.py": (
                "def sanitize_payload(data: dict) -> dict:\n"
                "    \"\"\"Strip whitespace and lower-case string values.\"\"\"\n"
                "    result = {}\n"
                "    for key, value in data.items():\n"
                "        if isinstance(value, str):\n"
                "            result[key] = value.strip().lower()\n"
                "        elif isinstance(value, list):\n"
                "            result[key] = [v.strip() if isinstance(v, str) else v for v in value]\n"  # noqa: E501
                "        else:\n"
                "            result[key] = value\n"
                "    return result\n"
                "\n"
                "\ndef update_profile(user_id: int, data: dict) -> dict:\n"
                "    clean = sanitize_payload(data)\n"
                "    return {'user_id': user_id, **clean}\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.MUTANT_DUPLICATE,
                file_path="svc/",
                should_detect=True,
                description="sanitize_payload is verbatim-copy-pasted across registration.py and profile_edit.py",  # noqa: E501
            ),
        ],
    ),
    evidence_url="https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-7529",
    bug_summary=(
        "Copy-paste duplicate validation function: when a security patch is applied "
        "to the original, the forgotten stale copy in the second service retains the "
        "old insecure logic."
    ),
    bug_class=BugClass.LOGIC,
    inspired_by_note=(
        "Transformative reproduction of the copy-paste-introduces-stale-copy bug class, "
        "inspired by CVE-2017-7529 (nginx range filter) and common Python service "
        "split patterns.  All names are original."
    ),
    pre_fix_note=(
        "svc/profile_edit.py contains a verbatim copy of sanitize_payload from "
        "svc/registration.py — when the original is patched, this copy will be forgotten."
    ),
    tags=["copy_paste", "stale_fix", "security_regression"],
)

# ── dc_004: Missing Authorization (MAZ) ──────────────────────────────────────
#
# Pattern class: Most API endpoints in a module are protected by an auth
# decorator.  One endpoint (typically added later) is missing the decorator,
# creating an access-control bypass.  OWASP A01:2021 — Broken Access Control.
#
# Evidence: https://owasp.org/Top10/A01_2021-Broken_Access_Control/
#           Multiple FastAPI/Flask CVEs share this pattern.

DC_004_MISSING_AUTHORIZATION = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_004_missing_authorization",
        description="dc_004 — Three Flask admin routes have @require_auth; admin_report was added without any auth decorator.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "api/__init__.py": "",
            "api/admin.py": (
                "from flask import Flask, jsonify\n"
                "\n"
                "app = Flask(__name__)\n"
                "\n"
                "\n"
                "@app.route('/admin/users', methods=['GET'])\n"
                "@require_auth\n"
                "def admin_list_users():\n"
                "    return jsonify({'users': []})\n"
                "\n"
                "\n"
                "@app.route('/admin/users/<int:user_id>', methods=['DELETE'])\n"
                "@require_auth\n"
                "def admin_delete_user(user_id: int):\n"
                "    return jsonify({'deleted': user_id})\n"
                "\n"
                "\n"
                "@app.route('/admin/settings', methods=['POST'])\n"
                "@require_auth\n"
                "def admin_update_settings():\n"
                "    return jsonify({'updated': True})\n"
                "\n"
                "\n"
                "@app.route('/admin/report', methods=['GET'])\n"
                "def admin_report():\n"
                "    return jsonify({'report': {}})\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.MISSING_AUTHORIZATION,
                file_path="api/admin.py",
                should_detect=True,
                description="admin_report is missing @require_auth unlike all other admin endpoints",  # noqa: E501
            ),
        ],
    ),
    evidence_url="https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
    bug_summary=(
        "OWASP A01 broken access control: admin_report endpoint is missing the "
        "@require_auth decorator that all other admin routes have."
    ),
    bug_class=BugClass.SECURITY,
    inspired_by_note=(
        "Transformative reproduction of the OWASP A01 broken-access-control pattern: "
        "one endpoint in a guarded module lacks the required auth decorator.  "
        "All names are original."
    ),
    pre_fix_note=(
        "api/admin.py has @require_auth on admin_list_users, admin_delete_user, and "
        "admin_update_settings, but admin_report was added without the decorator."
    ),
    tags=["missing_auth", "broken_access_control", "owasp_a01"],
)

# ── dc_005: Architecture Violation (AVS) ─────────────────────────────────────
#
# Pattern class: A service layer class imports directly from a database model
# module, bypassing the repository abstraction layer.  This creates a tight
# coupling between business logic and persistence implementation.
#
# Evidence: Clean Architecture (Uncle Bob); Django's "fat model" anti-pattern;
#           https://github.com/encode/django-rest-framework/issues/6403

DC_005_ARCHITECTURE_VIOLATION = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_005_architecture_violation",
        description="dc_005 — Repository layer imports from the Services layer, an upward layer violation.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "services/__init__.py": "",
            "services/pricing.py": (
                "def calculate_item_total(items: list) -> float:\n"
                "    return sum(item.get('price', 0.0) for item in items)\n"
            ),
            "repositories/__init__.py": "",
            "repositories/orders.py": (
                "# Architecture violation: DB/repository layer imports from service layer\n"
                "from services.pricing import calculate_item_total\n"
                "\n"
                "\nclass OrderRepository:\n"
                "    def get_total(self, order_id: int) -> float:\n"
                "        items = self._fetch_items(order_id)\n"
                "        return calculate_item_total(items)\n"
                "\n"
                "    def _fetch_items(self, order_id: int) -> list:\n"
                "        return []\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.ARCHITECTURE_VIOLATION,
                file_path="repositories/orders.py",
                should_detect=True,
                description="Repository (layer 2) imports from Services (layer 1) — upward violation",  # noqa: E501
            ),
        ],
    ),
    evidence_url="https://github.com/encode/django-rest-framework/issues/6403",
    bug_summary=(
        "Repository layer imports from the service layer (upward dependency), "
        "violating Clean Architecture: repositories should not depend on services."
    ),
    bug_class=BugClass.ARCHITECTURAL,
    inspired_by_note=(
        "Transformative reproduction of the clean-architecture upward-import pattern "
        "documented in django-rest-framework issue #6403 and Robert C. Martin's "
        "Clean Architecture.  All names are original."
    ),
    pre_fix_note=(
        "repositories/orders.py imports calculate_item_total from services/pricing.py "
        "instead of staying within the data layer."
    ),
    tags=["layer_violation", "clean_architecture", "upward_import"],
)

# ── dc_006: Pattern Fragmentation (PFS) ──────────────────────────────────────
#
# Pattern class: Multiple error handlers in the same module each use a
# different error-handling strategy: one re-raises, one logs and returns None,
# one swallows silently.  Inconsistent patterns make error behaviour
# unpredictable and create maintenance traps.
#
# Evidence: Flask error-handling inconsistency issues;
#           https://github.com/pallets/flask/blob/main/CHANGES.rst (multiple
#           error-handling consistency fixes across versions)

DC_006_PATTERN_FRAGMENTATION = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_006_pattern_fragmentation",
        description="dc_006 — Three error handlers in the same module each use incompatible strategies: re-raise, log+None, silent swallow.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "pipeline/__init__.py": "",
            "pipeline/processors.py": (
                "import logging\n"
                "\n"
                "logger = logging.getLogger(__name__)\n"
                "\n"
                "\n# Strategy 1: re-raise (correct for critical path)\n"
                "def process_payment(payload: dict) -> dict:\n"
                "    try:\n"
                "        return _charge(payload)\n"
                "    except ValueError as exc:\n"
                "        raise RuntimeError('Payment processing failed') from exc\n"
                "\n"
                "\n# Strategy 2: log + return None (loses error context for caller)\n"
                "def process_notification(payload: dict) -> dict | None:\n"
                "    try:\n"
                "        return _notify(payload)\n"
                "    except Exception as exc:\n"
                "        logger.error('Notification failed: %s', exc)\n"
                "        return None\n"
                "\n"
                "\n# Strategy 3: silent swallow (hides all failures)\n"
                "def process_audit_log(payload: dict) -> None:\n"
                "    try:\n"
                "        _audit(payload)\n"
                "    except Exception:\n"
                "        pass\n"
                "\n"
                "\ndef _charge(p: dict) -> dict:\n"
                "    return p\n"
                "\n"
                "\ndef _notify(p: dict) -> dict:\n"
                "    return p\n"
                "\n"
                "\ndef _audit(p: dict) -> None:\n"
                "    pass\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.PATTERN_FRAGMENTATION,
                file_path="pipeline/processors.py",
                should_detect=True,
                description="Three incompatible error-handling strategies in the same module",
            ),
        ],
    ),
    evidence_url="https://github.com/pallets/flask/blob/main/CHANGES.rst",
    bug_summary=(
        "Inconsistent error-handling patterns across handlers in the same module: "
        "re-raise, log+None, and silent swallow — makes error behaviour unpredictable."
    ),
    bug_class=BugClass.QUALITY,
    inspired_by_note=(
        "Transformative reproduction of the pattern-fragmentation / inconsistent-error-"
        "handling class documented across Flask CHANGES.rst entries.  All names original."
    ),
    pre_fix_note=(
        "pipeline/processors.py contains three handlers with three different exception "
        "strategies: re-raise, log+return-None, and silent pass — no single contract."
    ),
    tags=["error_handling", "inconsistency", "maintenance_trap"],
)

# ── dc_007: Guard Clause Deficit (GCD) ───────────────────────────────────────
#
# Pattern class: A function deeply nests logic rather than returning early on
# invalid input.  A missing None / empty guard at the top of the function
# leads to AttributeError or TypeError when callers pass unexpected values.
#
# Evidence: Martin Fowler "Replace Nested Conditional with Guard Clauses"
#           (Refactoring, 2nd ed.); FastAPI / Pydantic guard-clause patterns;
#           https://github.com/tiangolo/fastapi/issues/1624

DC_007_GUARD_CLAUSE_DEFICIT = DefectCorpusEntry(
    fixture=GroundTruthFixture(
        name="dc_007_guard_clause_deficit",
        description="dc_007 — build_invoice deeply nests None-unsafe attribute accesses instead of guarding at entry; at None input it raises AttributeError.",  # noqa: E501
        kind=FixtureKind.POSITIVE,
        files={
            "billing/__init__.py": "",
            "billing/invoices.py": (
                "def build_invoice(order: dict | None, customer: dict | None) -> dict:\n"
                "    result = {}\n"
                "    if order:\n"
                "        if order.get('items'):\n"
                "            if customer:\n"
                "                if customer.get('address'):\n"
                "                    result['line_items'] = order['items']\n"
                "                    result['ship_to'] = customer['address']\n"
                "                    if customer.get('email'):\n"
                "                        result['notify'] = customer['email']\n"
                "                        if order.get('discount'):\n"
                "                            result['discount'] = order['discount']\n"
                "    return result\n"
                "\n"
                "\ndef apply_tax(subtotal: float, jurisdiction: str) -> float:\n"
                "    if jurisdiction == 'us_ca':\n"
                "        rate = 0.0875\n"
                "    elif jurisdiction == 'us_ny':\n"
                "        rate = 0.08375\n"
                "    elif jurisdiction == 'eu_de':\n"
                "        rate = 0.19\n"
                "    elif jurisdiction == 'eu_fr':\n"
                "        rate = 0.20\n"
                "    else:\n"
                "        rate = 0.0\n"
                "    if subtotal > 10000:\n"
                "        rate = rate * 0.95\n"
                "    return subtotal * (1 + rate)\n"
                "\n"
                "\ndef format_line(item: dict, currency: str) -> str:\n"
                "    name = item.get('name', '')\n"
                "    qty = item.get('qty', 0)\n"
                "    price = item.get('price', 0.0)\n"
                "    if currency == 'USD':\n"
                "        symbol = '$'\n"
                "    elif currency == 'EUR':\n"
                "        symbol = 'E'\n"
                "    elif currency == 'GBP':\n"
                "        symbol = 'GBP'\n"
                "    elif currency == 'JPY':\n"
                "        symbol = 'Y'\n"
                "    else:\n"
                "        symbol = currency\n"
                "    if qty == 1:\n"
                "        return symbol + str(price) + ' ' + name\n"
                "    return str(qty) + ' x ' + symbol + str(price) + ' ' + name\n"
            ),
        },
        expected=[
            ExpectedFinding(
                signal_type=SignalType.GUARD_CLAUSE_DEFICIT,
                file_path="billing/invoices.py",
                should_detect=True,
                description="build_invoice uses six levels of nesting instead of early-return guards",  # noqa: E501
            ),
        ],
    ),
    evidence_url="https://github.com/tiangolo/fastapi/issues/1624",
    bug_summary=(
        "Deep nesting without guard clauses: build_invoice nests six levels deep "
        "rather than returning early on None/empty input, making the function "
        "brittle and hard to reason about."
    ),
    bug_class=BugClass.LOGIC,
    inspired_by_note=(
        "Transformative reproduction of the guard-clause-deficit pattern documented "
        "in Fowler's Refactoring and FastAPI issue #1624.  All names are original."
    ),
    pre_fix_note=(
        "billing/invoices.py uses six levels of nested if-statements in build_invoice "
        "instead of early-return guard clauses — deep nesting hides control flow."
    ),
    tags=["deep_nesting", "guard_clause", "attribute_error_risk"],
)


# ── Registry ──────────────────────────────────────────────────────────────────

ALL_DEFECT_CORPUS: list[DefectCorpusEntry] = [
    DC_001_CIRCULAR_IMPORT,
    DC_002_BROAD_EXCEPTION_MONOCULTURE,
    DC_003_MUTANT_DUPLICATE,
    DC_004_MISSING_AUTHORIZATION,
    DC_005_ARCHITECTURE_VIOLATION,
    DC_006_PATTERN_FRAGMENTATION,
    DC_007_GUARD_CLAUSE_DEFICIT,
]
