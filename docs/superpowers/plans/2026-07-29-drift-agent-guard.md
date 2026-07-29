# Drift Agent Guard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drift wird ein Claude-Code-Plugin, das im Agent-Loop meldet, wenn der Agent gerade Code dupliziert oder erstmals eine Verzeichnisgrenze überschreitet — schnell genug, um immer mitzulaufen.

**Architecture:** Ein vorberechneter SQLite-Index (`.drift/index.db`) hält Symbole und beobachtete Import-Kanten. Ein neues, importschlankes Modul `drift.guard` liest nur diesen Index und parst höchstens die eine geänderte Datei — es fasst `drift.cli` / `drift.pipeline` nie an. Claude-Code-Hooks rufen dieses Modul. Die bestehende Engine baut den Index offline und bleibt sonst unberührt.

**Tech Stack:** Python ≥3.11, ausschließlich Stdlib im heißen Pfad (`sqlite3`, `ast`, `hashlib`, `json`, `pathlib`, `argparse`). pytest für Tests. Claude-Code-Plugin-Manifest (JSON) + Shell-Hooks.

**Spec:** `docs/superpowers/specs/2026-07-29-drift-agent-guard-design.md` — bei jedem Zweifel gilt die Spec.

## Global Constraints

- **Keine neue Laufzeit-Dependency.** `pyproject.toml` `[project].dependencies` bleibt unverändert bei `click, rich, pyyaml, pydantic, gitpython, networkx`.
- **Heißer Pfad importfrei von schwerem Zeug.** Nach `import drift.guard` darf `sys.modules` keines von `transformers, sklearn, torch, numpy, scipy, networkx, rich, click, pydantic, drift.cli, drift.pipeline, drift.analyzer` enthalten. Das ist Gate G2 und wird als Test erzwungen.
- **Bestehende Engine wird nicht umgebaut.** Keine Änderung an `src/drift/signals/`, `src/drift/scoring/`, `src/drift/pipeline.py`, `src/drift/analyzer.py`. Keine bestehenden CLI-Commands entfernen oder umbenennen.
- **Latenzbudget:** `drift-guard pre` und `drift-guard post` je p95 ≤ 150 ms (Gate G1), gemessen als voller Prozessstart.
- **Oberfläche gedeckelt:** ≤ 2 MCP-Tools, ≤ 2 Slash-Commands, 0 Pflicht-Konfigdateien (Gate G4).
- **Der Guard blockiert nie.** Jeder Hook fängt jede Exception, schreibt eine Zeile nach stderr und beendet mit Exit-Code 0 und leerem stdout.
- **Schweigen ist der Normalfall.** Ohne Treffer wird nichts ausgegeben.
- **Schema-Version:** `SCHEMA_VERSION = 1`. Bei abweichender Version im Index wird der Index verworfen und neu gebaut — niemals migriert.
- **Sprache:** Code, Kommentare und Docstrings auf Englisch (Repo-Konvention). Nutzer-sichtbare Guard-Texte auf Englisch (das Tool ist englischsprachig).
- **Commits:** konventionell (`feat:`, `test:`, `fix:`, `docs:`, `ci:`), nach jedem Task mindestens einer.
- **Arbeitsverzeichnis:** Repo-Wurzel `/Users/moritzbecker/drift`. Python über `.venv/bin/python` bzw. `uv run`.

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `src/drift/guard/__init__.py` | Öffentliche Guard-API; **keine** schweren Importe |
| `src/drift/guard/schema.py` | SQL-Schema, `SCHEMA_VERSION`, Verbindungsaufbau, Staleness |
| `src/drift/guard/extract.py` | AST-Extraktion: Symbole + Import-Ziele aus **einer** Datei |
| `src/drift/guard/build.py` | Index bauen (voll + inkrementell) über `extract.py` |
| `src/drift/guard/lookup.py` | Duplikat- und Grenzkanten-Abfragen gegen den Index |
| `src/drift/guard/report.py` | Treffer → kurzer Nutzertext; Session-Zähler |
| `src/drift/guard/__main__.py` | Schlanke CLI: `pre`, `post`, `build`, `stats`, `doctor` |
| `.claude-plugin/plugin.json` | Plugin-Manifest (Hooks, Commands) |
| `.claude-plugin/marketplace.json` | Marketplace-Eintrag |
| `hooks/guard-session-start.sh` | SessionStart-Hook |
| `hooks/guard-pre-edit.sh` | PreToolUse(Write\|Edit) |
| `hooks/guard-post-edit.sh` | PostToolUse(Write\|Edit) |
| `hooks/guard-stop.sh` | Stop-Hook (Session-Bilanz) |
| `commands/drift-doctor.md` | Slash-Command `/drift:doctor` |
| `commands/drift-stats.md` | Slash-Command `/drift:stats` |
| `scripts/gates/measure_latency.py` | Gate G1 + Baseline-Messung |
| `tests/guard/fixtures/sample_repo/` | Ground-Truth-Korpus für Gate G3 |
| `tests/guard/test_*.py` | Tests je Modul |
| `tests/guard/test_gates.py` | G2, G3, G4 als Tests |

---

### Task 1: Gate-Harness und Baseline messen

Zuerst wird gemessen, was heute gilt. Ohne Baseline ist jede spätere Zahl wertlos.

**Files:**
- Create: `scripts/gates/measure_latency.py`
- Create: `tests/guard/test_measure_latency.py`
- Create: `tests/guard/__init__.py` (leer)
- Create: `benchmark_results/guard_baseline.json` (erzeugt, dann committet)

**Interfaces:**
- Consumes: nichts
- Produces: `measure(command: list[str], runs: int, cwd: str | None = None) -> dict` mit den Schlüsseln `command` (str), `runs` (int), `p50_ms` (float), `p95_ms` (float), `min_ms` (float), `max_ms` (float), `failures` (int)

- [ ] **Step 1: Write the failing test**

`tests/guard/test_measure_latency.py`:

```python
"""Tests for the latency measurement harness (gate G1)."""

import sys

from scripts.gates.measure_latency import measure


def test_measure_returns_percentiles_for_a_trivial_command():
    result = measure([sys.executable, "-c", "pass"], runs=5)

    assert result["runs"] == 5
    assert result["failures"] == 0
    assert result["min_ms"] <= result["p50_ms"] <= result["p95_ms"] <= result["max_ms"]
    assert result["p95_ms"] > 0


def test_measure_counts_failures_without_raising():
    result = measure([sys.executable, "-c", "raise SystemExit(3)"], runs=3)

    assert result["failures"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_measure_latency.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: Make `scripts` importable**

Create `scripts/__init__.py` (leer) und `scripts/gates/__init__.py` (leer).

- [ ] **Step 4: Write minimal implementation**

`scripts/gates/measure_latency.py`:

```python
"""Measure wall-clock latency of a command over N cold process starts.

Gate G1 of the Drift Agent Guard plan: the in-loop guard must stay under
150 ms p95. This harness is the single source of truth for that number, so
that every claim about latency is reproducible instead of asserted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time


def measure(command: list[str], runs: int, cwd: str | None = None) -> dict:
    """Run `command` `runs` times and return latency percentiles in ms."""
    durations: list[float] = []
    failures = 0
    for _ in range(runs):
        start = time.perf_counter()
        proc = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        durations.append((time.perf_counter() - start) * 1000.0)
        if proc.returncode != 0:
            failures += 1

    durations.sort()
    # Nearest-rank p95: smallest value at or above 95% of the sorted samples.
    p95_index = max(0, min(len(durations) - 1, int(round(0.95 * len(durations))) - 1))
    p50_index = max(0, min(len(durations) - 1, int(round(0.50 * len(durations))) - 1))
    return {
        "command": " ".join(command),
        "runs": runs,
        "p50_ms": round(durations[p50_index], 2),
        "p95_ms": round(durations[p95_index], 2),
        "min_ms": round(durations[0], 2),
        "max_ms": round(durations[-1], 2),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure command latency.")
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--out", default=None, help="Write JSON result here.")
    parser.add_argument("--label", default=None, help="Name for this measurement.")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        parser.error("no command given")

    result = measure(args.command, runs=args.runs)
    if args.label:
        result["label"] = args.label
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_measure_latency.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Baseline der heutigen Werte aufnehmen**

```bash
.venv/bin/python - <<'PY'
import json, sys
sys.path.insert(0, ".")
from scripts.gates.measure_latency import measure

PY_BIN = ".venv/bin/python"
baseline = {
    "measured_at": "2026-07-29",
    "note": "Baseline before Drift Agent Guard. Same harness measures the guard later.",
    "measurements": [
        dict(measure([PY_BIN, "-c", "import sqlite3, ast, json"], runs=20), label="floor_stdlib_import"),
        dict(measure([PY_BIN, "-c", "import drift.cli"], runs=10), label="import_drift_cli"),
        dict(measure([".venv/bin/drift", "--help"], runs=10), label="drift_help"),
    ],
}
with open("benchmark_results/guard_baseline.json", "w") as fh:
    json.dump(baseline, fh, indent=2)
print(json.dumps(baseline, indent=2))
PY
```

Erwartung laut Spec §3: `floor_stdlib_import` ≈ 20–40 ms, `import_drift_cli` und `drift_help` je 3000–3500 ms in dieser Dev-Umgebung (mit installiertem `[embeddings]`).

**Wichtig:** Ist `floor_stdlib_import` p95 bereits > 100 ms, dann ist das G1-Ziel von 150 ms nicht haltbar. In diesem Fall G1 in Spec und Plan auf `floor_p95 + 50 ms` anheben und die Änderung in `benchmark_results/guard_baseline.json` unter `"note"` begründen — **nicht** stillschweigend lockern.

- [ ] **Step 7: Commit**

```bash
git add scripts/__init__.py scripts/gates/__init__.py scripts/gates/measure_latency.py \
        tests/guard/__init__.py tests/guard/test_measure_latency.py \
        benchmark_results/guard_baseline.json
git commit -m "test: add latency gate harness and record pre-guard baseline"
```

---

### Task 2: Ground-Truth-Fixture-Repo (Basis für Gate G3)

Ohne Korpus mit bekannten Antworten ist „der Guard funktioniert" nicht prüfbar.

**Files:**
- Create: `tests/guard/fixtures/sample_repo/src/auth/tokens.py`
- Create: `tests/guard/fixtures/sample_repo/src/auth/session.py`
- Create: `tests/guard/fixtures/sample_repo/src/api/routes.py`
- Create: `tests/guard/fixtures/sample_repo/src/api/schemas.py`
- Create: `tests/guard/fixtures/sample_repo/src/db/models.py`
- Create: `tests/guard/fixtures/sample_repo/src/services/user_service.py`
- Create: `tests/guard/fixtures/sample_repo/expected.json`
- Create: `tests/guard/conftest.py`

**Interfaces:**
- Consumes: nichts
- Produces: pytest-Fixture `sample_repo(tmp_path) -> pathlib.Path` — kopiert das Fixture-Repo in ein tmp-Verzeichnis und gibt den Pfad zurück. Ferner `expected.json` mit den Schlüsseln `duplicate_cases` (Liste von `{file, symbol, expected_existing_at}`), `boundary_cases` (Liste von `{file, import_target, expected_novel_edge}`), `clean_files` (Liste von Pfaden, die **keine** Meldung erzeugen dürfen).

- [ ] **Step 1: Fixture-Quelldateien anlegen**

`tests/guard/fixtures/sample_repo/src/auth/tokens.py`:

```python
"""Token helpers."""


def validate_token(token, audience):
    return bool(token) and bool(audience)


def issue_token(user_id):
    return f"token-{user_id}"
```

`tests/guard/fixtures/sample_repo/src/auth/session.py`:

```python
"""Session helpers."""

from src.auth import tokens


def open_session(user_id):
    return tokens.issue_token(user_id)
```

`tests/guard/fixtures/sample_repo/src/api/routes.py`:

```python
"""HTTP routes."""

from src.services import user_service


def get_user(user_id):
    return user_service.load_user(user_id)
```

`tests/guard/fixtures/sample_repo/src/api/schemas.py`:

```python
"""Request and response shapes."""


def user_schema():
    return {"id": int, "name": str}
```

`tests/guard/fixtures/sample_repo/src/db/models.py`:

```python
"""Persistence layer."""


def fetch_user_row(user_id):
    return {"id": user_id, "name": "example"}
```

`tests/guard/fixtures/sample_repo/src/services/user_service.py`:

```python
"""Service layer between API and DB."""

from src.db import models


def load_user(user_id):
    return models.fetch_user_row(user_id)
```

- [ ] **Step 2: Erwartungen festschreiben**

`tests/guard/fixtures/sample_repo/expected.json`:

```json
{
  "description": "Ground truth for gate G3. Cases describe edits applied to the clean repo.",
  "duplicate_cases": [
    {
      "file": "src/api/schemas.py",
      "added_symbol": "validate_token",
      "expected_existing_at": "src/auth/tokens.py"
    },
    {
      "file": "src/services/user_service.py",
      "added_symbol": "validateToken",
      "expected_existing_at": "src/auth/tokens.py"
    }
  ],
  "boundary_cases": [
    {
      "file": "src/api/routes.py",
      "added_import": "src.db.models",
      "expected_novel_edge": ["src/api", "src/db"]
    }
  ],
  "clean_files": [
    "src/auth/session.py",
    "src/api/schemas.py",
    "src/services/user_service.py"
  ]
}
```

Hinweis: `clean_files` meint die **unveränderten** Dateien — sie dürfen im Ausgangszustand keine Meldung erzeugen. Die Duplikat-Fälle beschreiben Änderungen, die der Test erst anwendet.

- [ ] **Step 3: conftest schreiben**

`tests/guard/conftest.py`:

```python
"""Shared fixtures for guard tests."""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture
def sample_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """A writable copy of the ground-truth repo."""
    target = tmp_path / "sample_repo"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


@pytest.fixture
def expected() -> dict:
    """The ground-truth expectations for gate G3."""
    with open(FIXTURE_ROOT / "expected.json", encoding="utf-8") as handle:
        return json.load(handle)
```

- [ ] **Step 4: Fixture-Sanity-Test schreiben**

`tests/guard/test_fixtures.py`:

```python
"""The ground-truth corpus must stay well-formed."""


def test_sample_repo_has_all_source_files(sample_repo):
    paths = sorted(str(p.relative_to(sample_repo)) for p in sample_repo.rglob("*.py"))
    assert paths == [
        "src/api/routes.py",
        "src/api/schemas.py",
        "src/auth/session.py",
        "src/auth/tokens.py",
        "src/db/models.py",
        "src/services/user_service.py",
    ]


def test_expected_declares_cases(expected):
    assert len(expected["duplicate_cases"]) >= 2
    assert len(expected["boundary_cases"]) >= 1
    assert len(expected["clean_files"]) >= 3
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/guard/test_fixtures.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add tests/guard/fixtures tests/guard/conftest.py tests/guard/test_fixtures.py
git commit -m "test: add ground-truth fixture repo for guard gate G3"
```

---

### Task 3: Index-Schema, Verbindung und Staleness

**Files:**
- Create: `src/drift/guard/__init__.py`
- Create: `src/drift/guard/schema.py`
- Create: `tests/guard/test_schema.py`

**Interfaces:**
- Consumes: nichts
- Produces:
  - `SCHEMA_VERSION: int = 1`
  - `index_path(repo_root: pathlib.Path) -> pathlib.Path` → `<repo_root>/.drift/index.db`
  - `connect(repo_root, create: bool = False) -> sqlite3.Connection | None` — gibt `None` zurück, wenn kein Index existiert und `create=False`
  - `initialize(conn: sqlite3.Connection) -> None` — legt Tabellen an und schreibt `meta.schema_version`
  - `is_usable(conn: sqlite3.Connection) -> bool` — `False` bei fehlender/abweichender Schema-Version

- [ ] **Step 1: Write the failing test**

`tests/guard/test_schema.py`:

```python
"""Index schema lifecycle."""

import sqlite3

from drift.guard import schema


def test_connect_without_index_returns_none(tmp_path):
    assert schema.connect(tmp_path) is None


def test_initialize_creates_all_tables(tmp_path):
    conn = schema.connect(tmp_path, create=True)
    schema.initialize(conn)

    names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"meta", "files", "symbols", "import_edges"} <= names
    assert schema.is_usable(conn) is True


def test_index_lands_in_dot_drift(tmp_path):
    assert schema.index_path(tmp_path).parts[-2:] == (".drift", "index.db")


def test_wrong_schema_version_is_not_usable(tmp_path):
    conn = schema.connect(tmp_path, create=True)
    schema.initialize(conn)
    conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")

    assert schema.is_usable(conn) is False


def test_empty_database_is_not_usable(tmp_path):
    conn = sqlite3.connect(tmp_path / "bare.db")

    assert schema.is_usable(conn) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_schema.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'drift.guard'`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/__init__.py`:

```python
"""Drift Agent Guard — the in-loop hot path.

This package is deliberately import-light: it may only use the standard
library. Importing anything from ``drift.cli``, ``drift.pipeline`` or the
analysis engine here would re-introduce the multi-second import cost that
makes the guard unusable inside an agent loop. Gate G2 enforces this.
"""

SCHEMA_VERSION = 1

__all__ = ["SCHEMA_VERSION"]
```

`src/drift/guard/schema.py`:

```python
"""SQLite index: schema, connection handling, and usability checks."""

from __future__ import annotations

import pathlib
import sqlite3

SCHEMA_VERSION = 1

_TABLES = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    path       TEXT PRIMARY KEY,
    sha256     TEXT NOT NULL,
    indexed_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols (
    path      TEXT NOT NULL,
    name      TEXT NOT NULL,
    norm_name TEXT NOT NULL,
    kind      TEXT NOT NULL,
    sig_hash  TEXT NOT NULL,
    line      INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS import_edges (
    src_dir TEXT NOT NULL,
    dst_dir TEXT NOT NULL,
    count   INTEGER NOT NULL,
    PRIMARY KEY (src_dir, dst_dir)
);
CREATE INDEX IF NOT EXISTS idx_symbols_norm ON symbols(norm_name);
CREATE INDEX IF NOT EXISTS idx_symbols_sig  ON symbols(sig_hash);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
"""


def index_path(repo_root: pathlib.Path) -> pathlib.Path:
    """Location of the guard index for a repository."""
    return pathlib.Path(repo_root) / ".drift" / "index.db"


def connect(repo_root: pathlib.Path, create: bool = False) -> sqlite3.Connection | None:
    """Open the index. Returns None when it does not exist and create is False."""
    path = index_path(repo_root)
    if not path.exists():
        if not create:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    """Create tables and stamp the schema version."""
    conn.executescript(_TABLES)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def is_usable(conn: sqlite3.Connection) -> bool:
    """True when the index carries exactly the schema version we understand."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return False
    return bool(row) and row[0] == str(SCHEMA_VERSION)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_schema.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/drift/guard/__init__.py src/drift/guard/schema.py tests/guard/test_schema.py
git commit -m "feat(guard): add SQLite index schema and connection handling"
```

---

### Task 4: AST-Extraktion von Symbolen und Import-Zielen

**Files:**
- Create: `src/drift/guard/extract.py`
- Create: `tests/guard/test_extract.py`

**Interfaces:**
- Consumes: nichts
- Produces:
  - `STOPWORDS: frozenset[str]` — normalisierte Namen, die nie als Duplikat gemeldet werden
  - `normalize(name: str) -> str` — kleingeschrieben, Unterstriche entfernt
  - `signature_hash(kind: str, arg_names: list[str]) -> str` — 16-stelliger Hex-Digest
  - `Symbol` — `NamedTuple(name: str, norm_name: str, kind: str, sig_hash: str, line: int)`
  - `extract(source: str) -> tuple[list[Symbol], list[str]]` — Symbole und importierte Modulpfade (Punktnotation) einer Datei; bei Syntaxfehlern `([], [])`

- [ ] **Step 1: Write the failing test**

`tests/guard/test_extract.py`:

```python
"""AST extraction of symbols and import targets."""

from drift.guard import extract


def test_normalize_strips_case_and_underscores():
    assert extract.normalize("validate_token") == "validatetoken"
    assert extract.normalize("validateToken") == "validatetoken"
    assert extract.normalize("_private_helper") == "privatehelper"


def test_extract_finds_module_level_functions():
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    assert len(symbols) == 1
    assert symbols[0].name == "validate_token"
    assert symbols[0].norm_name == "validatetoken"
    assert symbols[0].kind == "function"
    assert symbols[0].line == 1


def test_extract_finds_classes():
    symbols, _ = extract.extract("class UserService:\n    pass\n")

    assert symbols[0].kind == "class"
    assert symbols[0].norm_name == "userservice"


def test_extract_ignores_methods_inside_classes():
    source = "class A:\n    def run(self):\n        return 1\n"
    symbols, _ = extract.extract(source)

    assert [s.name for s in symbols] == ["A"]


def test_signature_hash_is_order_insensitive_but_name_sensitive():
    a = extract.signature_hash("function", ["token", "audience"])
    b = extract.signature_hash("function", ["audience", "token"])
    c = extract.signature_hash("function", ["token", "issuer"])

    assert a == b
    assert a != c


def test_extract_collects_import_targets():
    source = "import os\nfrom src.db import models\nfrom src.db.models import fetch\n"
    _, imports = extract.extract(source)

    assert "os" in imports
    assert "src.db" in imports
    assert "src.db.models" in imports


def test_extract_survives_syntax_errors():
    assert extract.extract("def broken(:\n") == ([], [])


def test_common_names_are_stopwords():
    assert "main" in extract.STOPWORDS
    assert "run" in extract.STOPWORDS
    assert "validatetoken" not in extract.STOPWORDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_extract.py -v`
Expected: FAIL mit `ImportError: cannot import name 'extract'`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/extract.py`:

```python
"""Extract symbols and import targets from a single Python source file.

Only module-level functions and classes count as symbols. Methods are
excluded on purpose: ``run``, ``handle`` and friends repeat across every
class in a codebase and would drown the duplicate signal in noise.
"""

from __future__ import annotations

import ast
import hashlib
from typing import NamedTuple

#: Normalized names too common to ever be a meaningful duplicate.
STOPWORDS = frozenset(
    {
        "main",
        "run",
        "setup",
        "teardown",
        "handle",
        "handler",
        "init",
        "get",
        "set",
        "call",
        "process",
        "execute",
        "build",
        "create",
        "update",
        "delete",
        "test",
    }
)


class Symbol(NamedTuple):
    name: str
    norm_name: str
    kind: str
    sig_hash: str
    line: int


def normalize(name: str) -> str:
    """Lowercase and strip underscores so snake_case and camelCase collide."""
    return name.replace("_", "").lower()


def signature_hash(kind: str, arg_names: list[str]) -> str:
    """Stable digest over kind, arity and the set of argument names."""
    payload = f"{kind}|{len(arg_names)}|{','.join(sorted(arg_names))}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _arg_names(node: ast.AST) -> list[str]:
    args = getattr(node, "args", None)
    if args is None:
        return []
    collected = [a.arg for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)]
    return [a for a in collected if a not in ("self", "cls")]


def extract(source: str) -> tuple[list[Symbol], list[str]]:
    """Return (module-level symbols, imported module paths) for one file."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ([], [])

    symbols: list[Symbol] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "function"
            symbols.append(
                Symbol(
                    name=node.name,
                    norm_name=normalize(node.name),
                    kind=kind,
                    sig_hash=signature_hash(kind, _arg_names(node)),
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                Symbol(
                    name=node.name,
                    norm_name=normalize(node.name),
                    kind="class",
                    sig_hash=signature_hash("class", []),
                    line=node.lineno,
                )
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.append(node.module)
            imports.extend(f"{node.module}.{alias.name}" for alias in node.names)

    return (symbols, imports)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_extract.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/drift/guard/extract.py tests/guard/test_extract.py
git commit -m "feat(guard): extract module-level symbols and import targets via AST"
```

---

### Task 5: Index bauen (voll und inkrementell)

**Files:**
- Create: `src/drift/guard/build.py`
- Create: `tests/guard/test_build.py`

**Interfaces:**
- Consumes: `drift.guard.schema` (`connect`, `initialize`), `drift.guard.extract` (`extract`, `Symbol`)
- Produces:
  - `dir_of(rel_path: str) -> str` — Verzeichnisanteil eines repo-relativen Pfads, `"."` für Wurzeldateien
  - `module_to_dir(module: str, known_dirs: set[str]) -> str | None` — mappt `src.db.models` auf `src/db`, sofern bekannt
  - `build_full(repo_root: pathlib.Path) -> dict` — baut den Index neu; liefert `{"files": int, "symbols": int, "edges": int, "elapsed_ms": float}`
  - `update_file(repo_root: pathlib.Path, rel_path: str) -> None` — aktualisiert Symbole, Kanten und Datei-Hash für genau eine Datei

- [ ] **Step 1: Write the failing test**

`tests/guard/test_build.py`:

```python
"""Index building, full and incremental."""

from drift.guard import build, schema


def test_dir_of_handles_nesting_and_root():
    assert build.dir_of("src/db/models.py") == "src/db"
    assert build.dir_of("setup.py") == "."


def test_module_to_dir_maps_known_packages():
    known = {"src/db", "src/api"}

    assert build.module_to_dir("src.db.models", known) == "src/db"
    assert build.module_to_dir("src.db", known) == "src/db"
    assert build.module_to_dir("os.path", known) is None


def test_build_full_indexes_the_sample_repo(sample_repo):
    stats = build.build_full(sample_repo)

    assert stats["files"] == 6
    assert stats["symbols"] >= 7

    conn = schema.connect(sample_repo)
    names = {row[0] for row in conn.execute("SELECT norm_name FROM symbols")}
    assert "validatetoken" in names


def test_build_full_records_observed_import_edges(sample_repo):
    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    edges = {(row[0], row[1]) for row in conn.execute("SELECT src_dir, dst_dir FROM import_edges")}

    assert ("src/services", "src/db") in edges
    assert ("src/api", "src/services") in edges
    # The whole point: this edge does not exist yet.
    assert ("src/api", "src/db") not in edges


def test_update_file_replaces_symbols_for_that_file_only(sample_repo):
    build.build_full(sample_repo)
    target = sample_repo / "src" / "api" / "schemas.py"
    target.write_text("def brand_new_helper(x):\n    return x\n", encoding="utf-8")

    build.update_file(sample_repo, "src/api/schemas.py")

    conn = schema.connect(sample_repo)
    in_file = {
        row[0]
        for row in conn.execute(
            "SELECT norm_name FROM symbols WHERE path = ?", ("src/api/schemas.py",)
        )
    }
    elsewhere = {
        row[0]
        for row in conn.execute(
            "SELECT norm_name FROM symbols WHERE path = ?", ("src/auth/tokens.py",)
        )
    }
    assert in_file == {"brandnewhelper"}
    assert "validatetoken" in elsewhere
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_build.py -v`
Expected: FAIL mit `ImportError: cannot import name 'build'`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/build.py`:

```python
"""Build the guard index from a repository.

Full builds walk every Python file once. Incremental updates touch exactly
one file, which is what the PostToolUse hook does after each edit.
"""

from __future__ import annotations

import hashlib
import pathlib
import time

from drift.guard import extract, schema

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".drift",
    ".drift-cache",
    "build",
    "dist",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}


def dir_of(rel_path: str) -> str:
    """Directory part of a repo-relative path; '.' for files at the root."""
    parent = str(pathlib.PurePosixPath(rel_path).parent)
    return parent if parent != "" else "."


def module_to_dir(module: str, known_dirs: set[str]) -> str | None:
    """Map a dotted module path onto a repository directory, if it is one."""
    parts = module.split(".")
    while parts:
        candidate = "/".join(parts)
        if candidate in known_dirs:
            return candidate
        parts.pop()
    return None


def _iter_python_files(repo_root: pathlib.Path):
    for path in sorted(repo_root.rglob("*.py")):
        rel = path.relative_to(repo_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        yield rel.as_posix(), path


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_full(repo_root: pathlib.Path) -> dict:
    """Rebuild the index from scratch. Returns counts and elapsed time."""
    started = time.perf_counter()
    repo_root = pathlib.Path(repo_root)

    index_file = schema.index_path(repo_root)
    if index_file.exists():
        index_file.unlink()

    conn = schema.connect(repo_root, create=True)
    schema.initialize(conn)

    collected = list(_iter_python_files(repo_root))
    known_dirs = {dir_of(rel) for rel, _ in collected}

    edge_counts: dict[tuple[str, str], int] = {}
    symbol_rows: list[tuple] = []
    file_rows: list[tuple] = []
    now = time.time()

    for rel, path in collected:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        symbols, imports = extract.extract(source)
        src_dir = dir_of(rel)

        file_rows.append((rel, _sha256(path), now))
        symbol_rows.extend(
            (rel, s.name, s.norm_name, s.kind, s.sig_hash, s.line) for s in symbols
        )
        for module in imports:
            dst_dir = module_to_dir(module, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            edge_counts[(src_dir, dst_dir)] = edge_counts.get((src_dir, dst_dir), 0) + 1

    conn.executemany("INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)", file_rows)
    conn.executemany(
        "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        symbol_rows,
    )
    conn.executemany(
        "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, ?)",
        [(src, dst, count) for (src, dst), count in edge_counts.items()],
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('built_at', ?)", (str(now),)
    )
    conn.commit()
    conn.close()

    return {
        "files": len(file_rows),
        "symbols": len(symbol_rows),
        "edges": len(edge_counts),
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }


def update_file(repo_root: pathlib.Path, rel_path: str) -> None:
    """Refresh index rows for exactly one file. Silently no-ops without an index."""
    repo_root = pathlib.Path(repo_root)
    conn = schema.connect(repo_root)
    if conn is None or not schema.is_usable(conn):
        return

    path = repo_root / rel_path
    conn.execute("DELETE FROM symbols WHERE path = ?", (rel_path,))
    conn.execute("DELETE FROM files WHERE path = ?", (rel_path,))

    if path.exists():
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            conn.commit()
            conn.close()
            return
        symbols, imports = extract.extract(source)
        conn.executemany(
            "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(rel_path, s.name, s.norm_name, s.kind, s.sig_hash, s.line) for s in symbols],
        )
        conn.execute(
            "INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)",
            (rel_path, _sha256(path), time.time()),
        )
        known_dirs = {row[0] for row in conn.execute("SELECT DISTINCT src_dir FROM import_edges")}
        known_dirs |= {dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
        src_dir = dir_of(rel_path)
        for module in imports:
            dst_dir = module_to_dir(module, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            conn.execute(
                "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, 1)"
                " ON CONFLICT(src_dir, dst_dir) DO UPDATE SET count = count + 1",
                (src_dir, dst_dir),
            )

    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_build.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/drift/guard/build.py tests/guard/test_build.py
git commit -m "feat(guard): build symbol and import-edge index, full and incremental"
```

---

### Task 6: Lookups — Duplikate und neue Grenzkanten

**Files:**
- Create: `src/drift/guard/lookup.py`
- Create: `tests/guard/test_lookup.py`

**Interfaces:**
- Consumes: `drift.guard.schema`, `drift.guard.extract`, `drift.guard.build` (`dir_of`, `module_to_dir`)
- Produces:
  - `Hit` — `NamedTuple(kind: str, message: str)` mit `kind` aus `{"duplicate", "boundary"}`
  - `find_duplicates(conn, rel_path: str, symbols: list[extract.Symbol]) -> list[Hit]`
  - `find_novel_edges(conn, rel_path: str, imports: list[str]) -> list[Hit]`
  - `neighbourhood(conn, rel_path: str, limit: int = 8) -> list[str]` — Symbolnamen im selben Verzeichnis
  - `known_targets(conn, rel_path: str) -> list[str]` — Verzeichnisse, die dieses Verzeichnis bereits importiert

- [ ] **Step 1: Write the failing test**

`tests/guard/test_lookup.py`:

```python
"""Duplicate and boundary lookups against a built index."""

from drift.guard import build, extract, lookup, schema


def _conn(repo):
    build.build_full(repo)
    return schema.connect(repo)


def test_duplicate_is_reported_across_files(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    hits = lookup.find_duplicates(conn, "src/api/schemas.py", symbols)

    assert len(hits) == 1
    assert hits[0].kind == "duplicate"
    assert "src/auth/tokens.py" in hits[0].message
    assert "validate_token" in hits[0].message


def test_camel_case_rename_still_counts_as_duplicate(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validateToken(a, b):\n    return True\n")

    hits = lookup.find_duplicates(conn, "src/services/user_service.py", symbols)

    assert len(hits) == 1


def test_symbol_in_its_own_file_is_not_a_duplicate(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    assert lookup.find_duplicates(conn, "src/auth/tokens.py", symbols) == []


def test_stopword_names_are_never_duplicates(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def run(self):\n    return 1\n")

    assert lookup.find_duplicates(conn, "src/api/schemas.py", symbols) == []


def test_novel_edge_is_reported(sample_repo):
    conn = _conn(sample_repo)

    hits = lookup.find_novel_edges(conn, "src/api/routes.py", ["src.db.models"])

    assert len(hits) == 1
    assert hits[0].kind == "boundary"
    assert "src/api" in hits[0].message and "src/db" in hits[0].message


def test_existing_edge_is_silent(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.find_novel_edges(conn, "src/api/routes.py", ["src.services.user_service"]) == []


def test_stdlib_imports_are_silent(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.find_novel_edges(conn, "src/api/routes.py", ["os", "json.decoder"]) == []


def test_neighbourhood_lists_sibling_symbols(sample_repo):
    conn = _conn(sample_repo)

    names = lookup.neighbourhood(conn, "src/auth/session.py")

    assert "validate_token" in names
    assert "issue_token" in names


def test_known_targets_lists_existing_edges(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.known_targets(conn, "src/api/routes.py") == ["src/services"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_lookup.py -v`
Expected: FAIL mit `ImportError: cannot import name 'lookup'`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/lookup.py`:

```python
"""Answer the two guard questions with index lookups only.

1. Does this symbol already exist somewhere else?
2. Does this import cross a directory boundary that has never been crossed?
"""

from __future__ import annotations

import sqlite3
from typing import NamedTuple

from drift.guard import build, extract


class Hit(NamedTuple):
    kind: str
    message: str


def find_duplicates(
    conn: sqlite3.Connection, rel_path: str, symbols: list[extract.Symbol]
) -> list[Hit]:
    """Symbols that already exist elsewhere in the repository."""
    hits: list[Hit] = []
    for symbol in symbols:
        if symbol.norm_name in extract.STOPWORDS:
            continue
        row = conn.execute(
            "SELECT path, name, line FROM symbols"
            " WHERE norm_name = ? AND path != ? ORDER BY path LIMIT 1",
            (symbol.norm_name, rel_path),
        ).fetchone()
        if row is None:
            continue
        other_path, other_name, other_line = row
        hits.append(
            Hit(
                kind="duplicate",
                message=(
                    f"`{symbol.name}` already exists as `{other_name}` "
                    f"in {other_path}:{other_line}"
                ),
            )
        )
    return hits


def find_novel_edges(
    conn: sqlite3.Connection, rel_path: str, imports: list[str]
) -> list[Hit]:
    """Imports that introduce a directory-to-directory edge seen nowhere yet."""
    known_dirs = {build.dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
    src_dir = build.dir_of(rel_path)
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT dst_dir FROM import_edges WHERE src_dir = ?", (src_dir,)
        )
    }

    hits: list[Hit] = []
    reported: set[str] = set()
    for module in imports:
        dst_dir = build.module_to_dir(module, known_dirs)
        if dst_dir is None or dst_dir == src_dir:
            continue
        if dst_dir in existing or dst_dir in reported:
            continue
        reported.add(dst_dir)
        hits.append(
            Hit(
                kind="boundary",
                message=(
                    f"first import from {src_dir}/ into {dst_dir}/ "
                    f"anywhere in this repository"
                ),
            )
        )
    return hits


def neighbourhood(conn: sqlite3.Connection, rel_path: str, limit: int = 8) -> list[str]:
    """Symbol names that already live in the same directory."""
    src_dir = build.dir_of(rel_path)
    like = "%" if src_dir == "." else f"{src_dir}/%"
    rows = conn.execute(
        "SELECT DISTINCT name FROM symbols WHERE path LIKE ? AND path != ?"
        " ORDER BY name LIMIT ?",
        (like, rel_path, limit),
    )
    return [row[0] for row in rows]


def known_targets(conn: sqlite3.Connection, rel_path: str) -> list[str]:
    """Directories this file's directory already imports from."""
    src_dir = build.dir_of(rel_path)
    rows = conn.execute(
        "SELECT dst_dir FROM import_edges WHERE src_dir = ? ORDER BY dst_dir", (src_dir,)
    )
    return [row[0] for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_lookup.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add src/drift/guard/lookup.py tests/guard/test_lookup.py
git commit -m "feat(guard): duplicate and novel-boundary lookups"
```

---

### Task 7: Report-Formatierung und ehrlicher Session-Zähler

Gate G7: der Zähler zählt nur, was ein Test als echt reproduziert.

**Files:**
- Create: `src/drift/guard/report.py`
- Create: `tests/guard/test_report.py`

**Interfaces:**
- Consumes: `drift.guard.lookup` (`Hit`)
- Produces:
  - `MAX_MESSAGE_CHARS: int = 500`
  - `format_hits(hits: list[lookup.Hit]) -> str` — leerer String bei leerer Liste
  - `counter_path(repo_root) -> pathlib.Path` → `<repo_root>/.drift/session_counter.json`
  - `bump(repo_root, kind: str, amount: int = 1) -> None`
  - `read_counter(repo_root) -> dict` — `{"duplicate": int, "boundary": int}`
  - `reset_counter(repo_root) -> None`
  - `summary_line(counts: dict) -> str`

- [ ] **Step 1: Write the failing test**

`tests/guard/test_report.py`:

```python
"""Guard output formatting and the session counter."""

from drift.guard import lookup, report


def test_no_hits_produces_no_output():
    assert report.format_hits([]) == ""


def test_hits_are_prefixed_and_bounded():
    hits = [
        lookup.Hit("duplicate", "`validate_token` already exists in src/auth/tokens.py:4"),
        lookup.Hit("boundary", "first import from src/api/ into src/db/"),
    ]

    text = report.format_hits(hits)

    assert text.startswith("drift:")
    assert "validate_token" in text
    assert "src/db/" in text
    assert len(text) <= report.MAX_MESSAGE_CHARS


def test_long_hit_lists_are_truncated():
    hits = [lookup.Hit("duplicate", "x" * 200) for _ in range(10)]

    assert len(report.format_hits(hits)) <= report.MAX_MESSAGE_CHARS


def test_counter_starts_at_zero(tmp_path):
    assert report.read_counter(tmp_path) == {"duplicate": 0, "boundary": 0}


def test_bump_accumulates_per_kind(tmp_path):
    report.bump(tmp_path, "duplicate")
    report.bump(tmp_path, "duplicate")
    report.bump(tmp_path, "boundary")

    assert report.read_counter(tmp_path) == {"duplicate": 2, "boundary": 1}


def test_reset_clears_the_counter(tmp_path):
    report.bump(tmp_path, "duplicate")
    report.reset_counter(tmp_path)

    assert report.read_counter(tmp_path) == {"duplicate": 0, "boundary": 0}


def test_summary_line_states_zero_honestly():
    assert "0" in report.summary_line({"duplicate": 0, "boundary": 0})


def test_summary_line_reports_actual_counts():
    line = report.summary_line({"duplicate": 3, "boundary": 1})

    assert "3" in line and "1" in line
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/guard/test_report.py -v`
Expected: FAIL mit `ImportError: cannot import name 'report'`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/report.py`:

```python
"""Turn hits into short agent-facing text, and keep an honest session tally.

The counter only ever increments from a real hit produced by lookup.py.
Nothing here fabricates or estimates a number.
"""

from __future__ import annotations

import json
import pathlib

from drift.guard import lookup

MAX_MESSAGE_CHARS = 500
_KINDS = ("duplicate", "boundary")


def format_hits(hits: list[lookup.Hit]) -> str:
    """Compact message for the agent. Empty string when there is nothing to say."""
    if not hits:
        return ""
    lines = ["drift:"]
    for hit in hits:
        candidate = f"  - {hit.message}"
        projected = "\n".join(lines + [candidate])
        if len(projected) > MAX_MESSAGE_CHARS:
            lines.append("  - (more findings omitted)")
            break
        lines.append(candidate)
    text = "\n".join(lines)
    return text[:MAX_MESSAGE_CHARS]


def counter_path(repo_root) -> pathlib.Path:
    return pathlib.Path(repo_root) / ".drift" / "session_counter.json"


def read_counter(repo_root) -> dict:
    path = counter_path(repo_root)
    if not path.exists():
        return {kind: 0 for kind in _KINDS}
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return {kind: 0 for kind in _KINDS}
    return {kind: int(stored.get(kind, 0)) for kind in _KINDS}


def bump(repo_root, kind: str, amount: int = 1) -> None:
    if kind not in _KINDS:
        return
    counts = read_counter(repo_root)
    counts[kind] += amount
    path = counter_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(counts, handle)


def reset_counter(repo_root) -> None:
    path = counter_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({kind: 0 for kind in _KINDS}, handle)


def summary_line(counts: dict) -> str:
    return (
        f"drift: {counts.get('duplicate', 0)} duplicate(s) flagged, "
        f"{counts.get('boundary', 0)} new boundary crossing(s) this session"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/guard/test_report.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/drift/guard/report.py tests/guard/test_report.py
git commit -m "feat(guard): format hits and track an honest session counter"
```

---

### Task 8: Schlanke CLI `drift-guard` und Import-Hygiene-Gate (G2)

**Files:**
- Create: `src/drift/guard/__main__.py`
- Create: `tests/guard/test_cli.py`
- Create: `tests/guard/test_gates.py`
- Modify: `pyproject.toml` — Console-Script `drift-guard` ergänzen

**Interfaces:**
- Consumes: alle bisherigen Guard-Module
- Produces: Kommandozeile
  - `drift-guard build [--repo PATH]` → JSON-Statistik auf stdout
  - `drift-guard pre --file REL [--repo PATH]` → Guard-Text **nur wenn die Datei noch nicht existiert**, sonst nichts
  - `drift-guard post --file REL [--repo PATH]` → Guard-Text oder nichts; erhöht den Zähler; aktualisiert den Index
  - `drift-guard stats [--repo PATH]` → Bilanzzeile
  - `drift-guard reset [--repo PATH]` → setzt den Session-Zähler auf 0
  - `drift-guard doctor [--repo PATH]` → Checkliste, Exit 0 bei allen `[x]`, Exit 1 sonst
  - Alle Unterkommandos beenden bei internem Fehler mit Exit 0 und leerem stdout

- [ ] **Step 1: Write the failing tests**

`tests/guard/test_cli.py`:

```python
"""The lean guard CLI."""

import json
import subprocess
import sys

from drift.guard import build, report


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "drift.guard", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_build_reports_counts(sample_repo):
    result = _run("build", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert json.loads(result.stdout)["files"] == 6


def test_pre_is_silent_for_files_that_already_exist(sample_repo):
    build.build_full(sample_repo)

    result = _run("pre", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_pre_briefs_the_agent_when_a_new_file_is_created(sample_repo):
    build.build_full(sample_repo)

    result = _run("pre", "--repo", str(sample_repo), "--file", "src/api/handlers.py")

    assert result.returncode == 0
    assert "src/services" in result.stdout
    assert "get_user" in result.stdout


def test_reset_clears_the_counter(sample_repo):
    build.build_full(sample_repo)
    report.bump(sample_repo, "boundary")

    result = _run("reset", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert report.read_counter(sample_repo) == {"duplicate": 0, "boundary": 0}


def test_post_reports_a_duplicate_and_bumps_the_counter(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "schemas.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )

    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/schemas.py")

    assert result.returncode == 0
    assert "validate_token" in result.stdout
    assert report.read_counter(sample_repo)["duplicate"] == 1


def test_post_reports_a_novel_boundary_crossing(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "routes.py").write_text(
        "from src.db import models\n\n\ndef get_user(user_id):\n"
        "    return models.fetch_user_row(user_id)\n",
        encoding="utf-8",
    )

    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert "src/db" in result.stdout
    assert report.read_counter(sample_repo)["boundary"] == 1


def test_post_without_an_index_is_silent_and_succeeds(sample_repo):
    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_stats_prints_the_summary(sample_repo):
    build.build_full(sample_repo)
    report.bump(sample_repo, "duplicate")

    result = _run("stats", "--repo", str(sample_repo))

    assert "1 duplicate" in result.stdout


def test_doctor_passes_on_a_built_repo(sample_repo):
    build.build_full(sample_repo)

    result = _run("doctor", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert "[x]" in result.stdout


def test_doctor_fails_without_an_index(sample_repo):
    result = _run("doctor", "--repo", str(sample_repo))

    assert result.returncode == 1
    assert "[ ]" in result.stdout
```

`tests/guard/test_gates.py` (nur der G2-Teil in diesem Task; G3 und G4 folgen in Task 9 und 10):

```python
"""Hard gates from the Drift Agent Guard plan."""

import subprocess
import sys

FORBIDDEN_IN_HOT_PATH = [
    "transformers",
    "sentence_transformers",
    "sklearn",
    "torch",
    "numpy",
    "scipy",
    "networkx",
    "rich",
    "click",
    "pydantic",
    "drift.cli",
    "drift.pipeline",
    "drift.analyzer",
]


def test_gate_g2_hot_path_imports_nothing_heavy():
    """G2: importing the guard must not drag in the analysis engine."""
    probe = (
        "import sys\n"
        "import drift.guard, drift.guard.schema, drift.guard.extract, "
        "drift.guard.build, drift.guard.lookup, drift.guard.report\n"
        f"forbidden = {FORBIDDEN_IN_HOT_PATH!r}\n"
        "found = sorted(m for m in forbidden if m in sys.modules)\n"
        "print(','.join(found))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "", f"heavy modules leaked into the hot path: {result.stdout}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/guard/test_cli.py tests/guard/test_gates.py -v`
Expected: FAIL — `No module named drift.guard.__main__`

- [ ] **Step 3: Write minimal implementation**

`src/drift/guard/__main__.py`:

```python
"""Lean command line for the guard hot path.

Deliberately argparse and not click: click alone costs tens of milliseconds
of import time on every hook invocation, and this entry point runs twice per
file edit.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from drift.guard import build, extract, lookup, report, schema


def _open_index(repo_root: pathlib.Path):
    conn = schema.connect(repo_root)
    if conn is None or not schema.is_usable(conn):
        return None
    return conn


def _cmd_build(args) -> int:
    stats = build.build_full(pathlib.Path(args.repo))
    print(json.dumps(stats))
    return 0


def _cmd_pre(args) -> int:
    """Brief the agent only when it is about to create a NEW file.

    Editing an existing file is the common case; speaking up every time would
    make the guard noise instead of signal. A new file is where duplication is
    actually born, and it is rare enough to be worth a sentence.
    """
    repo_root = pathlib.Path(args.repo)
    if (repo_root / args.file).exists():
        return 0

    conn = _open_index(repo_root)
    if conn is None:
        return 0
    targets = lookup.known_targets(conn, args.file)
    neighbours = lookup.neighbourhood(conn, args.file)
    conn.close()

    lines: list[str] = []
    if neighbours:
        lines.append(f"  - already defined in {build.dir_of(args.file)}/: {', '.join(neighbours)}")
    if targets:
        lines.append(f"  - {build.dir_of(args.file)}/ so far imports only from: {', '.join(targets)}")
    if not lines:
        return 0
    text = "\n".join(["drift:", *lines])[: report.MAX_MESSAGE_CHARS]
    print(text)
    return 0


def _cmd_reset(args) -> int:
    report.reset_counter(pathlib.Path(args.repo))
    return 0


def _cmd_post(args) -> int:
    repo_root = pathlib.Path(args.repo)
    conn = _open_index(repo_root)
    if conn is None:
        return 0

    path = repo_root / args.file
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        conn.close()
        return 0

    symbols, imports = extract.extract(source)
    hits = lookup.find_duplicates(conn, args.file, symbols)
    hits += lookup.find_novel_edges(conn, args.file, imports)
    conn.close()

    for hit in hits:
        report.bump(repo_root, hit.kind)

    build.update_file(repo_root, args.file)

    text = report.format_hits(hits)
    if text:
        print(text)
    return 0


def _cmd_stats(args) -> int:
    print(report.summary_line(report.read_counter(pathlib.Path(args.repo))))
    return 0


def _cmd_doctor(args) -> int:
    repo_root = pathlib.Path(args.repo)
    checks: list[tuple[bool, str]] = []

    index_file = schema.index_path(repo_root)
    checks.append((index_file.exists(), f"index present at {index_file}"))

    conn = schema.connect(repo_root)
    usable = conn is not None and schema.is_usable(conn)
    checks.append((usable, f"index schema version is {schema.SCHEMA_VERSION}"))

    file_count = 0
    if usable:
        file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
    checks.append((file_count > 0, f"index holds {file_count} file(s)"))

    for ok, label in checks:
        print(f"[{'x' if ok else ' '}] {label}")
    return 0 if all(ok for ok, _ in checks) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drift-guard", description="Drift agent guard.")
    parser.add_argument("--repo", default=".", help="Repository root.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="Build the guard index.")
    for name in ("pre", "post"):
        p = sub.add_parser(name, help=f"Guard {name}-edit check.")
        p.add_argument("--file", required=True, help="Repo-relative file path.")
    sub.add_parser("stats", help="Print the session tally.")
    sub.add_parser("reset", help="Reset the session tally.")
    sub.add_parser("doctor", help="Check the guard installation.")

    args = parser.parse_args(argv)
    handlers = {
        "build": _cmd_build,
        "pre": _cmd_pre,
        "post": _cmd_post,
        "stats": _cmd_stats,
        "reset": _cmd_reset,
        "doctor": _cmd_doctor,
    }
    try:
        return handlers[args.command](args)
    except Exception as exc:  # never break the agent loop
        print(f"drift-guard: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Console-Script registrieren**

In `pyproject.toml` unter `[project.scripts]` **ergänzen** (bestehende Zeilen unverändert lassen):

```toml
drift-guard = "drift.guard.__main__:main"
```

Danach: `.venv/bin/python -m pip install -e . --no-deps` (oder `uv sync`), damit `drift-guard` verfügbar ist.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/guard/test_cli.py tests/guard/test_gates.py -v`
Expected: PASS (10 passed)

Schlägt G2 fehl, ist irgendwo ein Import aus dem Engine-Teil hereingerutscht — nicht die Verbotsliste kürzen, sondern den Import entfernen.

- [ ] **Step 6: Commit**

```bash
git add src/drift/guard/__main__.py tests/guard/test_cli.py tests/guard/test_gates.py pyproject.toml
git commit -m "feat(guard): add lean drift-guard CLI and enforce hot-path import hygiene"
```

---

### Task 9: Latenz-Gate G1 und Inhalts-Gate G3 scharf schalten

**Files:**
- Modify: `tests/guard/test_gates.py` — G1 und G3 ergänzen
- Create: `scripts/gates/run_all_gates.py`
- Modify: `benchmark_results/guard_baseline.json` — Guard-Messung anhängen

**Interfaces:**
- Consumes: `scripts.gates.measure_latency.measure`, `drift.guard.build`, `drift.guard.lookup`
- Produces: `run_all_gates.py` mit Exit 0 nur, wenn alle Gates bestehen

- [ ] **Step 1: G1- und G3-Tests schreiben**

An `tests/guard/test_gates.py` anhängen — die Importzeile ganz oben in der Datei ergänzen, den Rest
unten anfügen:

```python
# --- top of file: extend the existing imports ---
import json
import pathlib
import sys
import time

import pytest

from drift.guard import build, extract, lookup, report, schema
from scripts.gates.measure_latency import measure

# --- append below ---
LATENCY_BUDGET_MS = 150.0


@pytest.mark.performance
def test_gate_g1_pre_and_post_stay_within_budget(sample_repo):
    """G1: the in-loop guard must stay under the latency budget, cold start."""
    build.build_full(sample_repo)

    for command in ("pre", "post"):
        result = measure(
            [
                sys.executable,
                "-m",
                "drift.guard",
                command,
                "--repo",
                str(sample_repo),
                "--file",
                "src/api/routes.py",
            ],
            runs=20,
        )
        assert result["failures"] == 0
        assert result["p95_ms"] <= LATENCY_BUDGET_MS, (
            f"{command}: p95 {result['p95_ms']} ms exceeds {LATENCY_BUDGET_MS} ms"
        )


def _expected_cases() -> dict:
    path = (
        pathlib.Path(__file__).parent / "fixtures" / "sample_repo" / "expected.json"
    )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_gate_g3_recall_on_ground_truth(sample_repo):
    """G3a: every planted duplicate and boundary crossing must be reported."""
    build.build_full(sample_repo)
    cases = _expected_cases()
    conn = schema.connect(sample_repo)
    detected = 0
    total = 0

    for case in cases["duplicate_cases"]:
        total += 1
        symbols, _ = extract.extract(f"def {case['added_symbol']}(a, b):\n    return None\n")
        hits = lookup.find_duplicates(conn, case["file"], symbols)
        if hits and case["expected_existing_at"] in hits[0].message:
            detected += 1

    for case in cases["boundary_cases"]:
        total += 1
        hits = lookup.find_novel_edges(conn, case["file"], [case["added_import"]])
        src, dst = case["expected_novel_edge"]
        if hits and src in hits[0].message and dst in hits[0].message:
            detected += 1

    assert detected / total >= 0.9, f"recall {detected}/{total} below 90%"


def test_gate_g3_no_false_positives_on_clean_files(sample_repo):
    """G3b: untouched files must produce no findings at all."""
    build.build_full(sample_repo)
    cases = _expected_cases()
    conn = schema.connect(sample_repo)

    for rel_path in cases["clean_files"]:
        source = (sample_repo / rel_path).read_text(encoding="utf-8")
        symbols, imports = extract.extract(source)
        hits = lookup.find_duplicates(conn, rel_path, symbols)
        hits += lookup.find_novel_edges(conn, rel_path, imports)

        assert hits == [], f"{rel_path} produced unexpected findings: {hits}"
```

- [ ] **Step 2: Run tests to verify status**

Run: `.venv/bin/python -m pytest tests/guard/test_gates.py -v`
Expected: G2 und G3 PASS. G1 kann beim ersten Lauf fehlschlagen.

- [ ] **Step 3: Bei G1-Fehlschlag optimieren**

Reihenfolge der Maßnahmen, teuerste zuletzt:
1. Prüfen, ob `drift/__init__.py` beim Import etwas Schweres zieht — falls ja, im Guard-Pfad `drift.guard` als eigenständiges Top-Level-Paket ansprechen oder den Import in `drift/__init__.py` faul machen (**ohne** bestehendes Verhalten zu ändern).
2. `sqlite3`-Verbindungen nur öffnen, wenn tatsächlich gebraucht.
3. `from __future__ import annotations` überall (bereits gesetzt) und keine Typ-Importe zur Laufzeit.
4. Messen nach jedem Schritt mit `measure_latency.py`, nicht raten.

Bleibt die Untergrenze aus Task 1 (`floor_stdlib_import`) über 100 ms, dann `LATENCY_BUDGET_MS` auf `floor_p95 + 50` setzen und die Begründung in `benchmark_results/guard_baseline.json` festhalten.

- [ ] **Step 4: Sammel-Gate-Skript schreiben**

`scripts/gates/run_all_gates.py`:

```python
"""Run every hard gate of the Drift Agent Guard and report pass/fail.

Exit code 0 only when all gates pass. Used by CI and by humans who want one
command that answers "is this done?".
"""

from __future__ import annotations

import subprocess
import sys

GATES = [
    ("G1 latency", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g1_pre_and_post_stay_within_budget", "-q"]),
    ("G2 import hygiene", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g2_hot_path_imports_nothing_heavy", "-q"]),
    ("G3 recall", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g3_recall_on_ground_truth", "-q"]),
    ("G3 precision", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g3_no_false_positives_on_clean_files", "-q"]),
    ("G4 surface", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g4_surface_stays_small", "-q"]),
    ("G6 index build", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g6_index_build_is_fast_enough", "-q"]),
    ("G7 counter honesty", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g7_counter_only_counts_real_hits", "-q"]),
]


def main() -> int:
    failed = []
    for label, args in GATES:
        proc = subprocess.run([sys.executable, *args])
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"[{status}] {label}")
        if proc.returncode != 0:
            failed.append(label)
    if failed:
        print(f"\n{len(failed)} gate(s) failed: {', '.join(failed)}")
        return 1
    print("\nall gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Hinweis: G4, G6 und G7 werden in Task 10 und 11 ergänzt; bis dahin meldet das Skript für sie FAIL. Das ist beabsichtigt und zeigt den Restweg.

- [ ] **Step 5: Guard-Messung in die Baseline aufnehmen**

```bash
.venv/bin/python - <<'PY'
import json, subprocess, sys, tempfile, shutil, pathlib
sys.path.insert(0, ".")
from scripts.gates.measure_latency import measure
from drift.guard import build

tmp = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree("tests/guard/fixtures/sample_repo", tmp)
build.build_full(tmp)

with open("benchmark_results/guard_baseline.json") as fh:
    data = json.load(fh)
for cmd in ("pre", "post"):
    data["measurements"].append(dict(measure(
        [sys.executable, "-m", "drift.guard", cmd, "--repo", str(tmp), "--file", "src/api/routes.py"],
        runs=20), label=f"guard_{cmd}"))
with open("benchmark_results/guard_baseline.json", "w") as fh:
    json.dump(data, fh, indent=2)
print(json.dumps(data["measurements"][-2:], indent=2))
PY
```

- [ ] **Step 6: Commit**

```bash
git add tests/guard/test_gates.py scripts/gates/run_all_gates.py benchmark_results/guard_baseline.json
git commit -m "test: enforce guard latency (G1) and ground-truth accuracy (G3)"
```

---

### Task 10: Claude-Code-Plugin — Manifest, Hooks, Oberflächen-Gate (G4)

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `hooks/guard-session-start.sh`
- Create: `hooks/guard-pre-edit.sh`
- Create: `hooks/guard-post-edit.sh`
- Create: `hooks/guard-stop.sh`
- Create: `commands/drift-doctor.md`
- Create: `commands/drift-stats.md`
- Modify: `tests/guard/test_gates.py` — G4 ergänzen
- Create: `tests/guard/test_hooks.py`

**Interfaces:**
- Consumes: `drift-guard` Console-Script aus Task 8
- Produces: Hook-Skripte, die JSON vom stdin lesen (`tool_input.file_path`) und Guard-Text auf stdout schreiben

- [ ] **Step 1: Hook-Test schreiben**

`tests/guard/test_hooks.py`:

```python
"""The shell hooks that Claude Code invokes."""

import json
import os
import pathlib
import subprocess
import sys

from drift.guard import build

HOOKS = pathlib.Path(__file__).resolve().parents[2] / "hooks"


def _env():
    """Make the interpreter running the tests reachable from inside the hook.

    The hooks resolve `drift-guard` from PATH; under pytest that binary lives in
    the same directory as the interpreter, which is not necessarily on PATH.
    """
    env = dict(os.environ)
    env["PATH"] = str(pathlib.Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return env


def _run_hook(name, payload, cwd):
    return subprocess.run(
        ["bash", str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=_env(),
    )


def test_post_edit_hook_reports_a_duplicate(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "schemas.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )

    result = _run_hook(
        "guard-post-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "src" / "api" / "schemas.py")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    assert "validate_token" in result.stdout


def test_hooks_exit_zero_on_garbage_input(sample_repo):
    result = subprocess.run(
        ["bash", str(HOOKS / "guard-post-edit.sh")],
        input="not json at all",
        capture_output=True,
        text=True,
        cwd=sample_repo,
    )

    assert result.returncode == 0


def test_hooks_ignore_non_python_files(sample_repo):
    build.build_full(sample_repo)

    result = _run_hook(
        "guard-post-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "README.md")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""
```

An `tests/guard/test_gates.py` anhängen:

```python
def test_gate_g4_surface_stays_small():
    """G4: the plugin surface must stay at or below two tools and two commands."""
    root = pathlib.Path(__file__).resolve().parents[2]
    with open(root / ".claude-plugin" / "plugin.json", encoding="utf-8") as handle:
        manifest = json.load(handle)

    tools = manifest.get("mcpServers", {})
    commands = list((root / "commands").glob("drift-*.md"))

    assert len(tools) <= 1, "at most one MCP server"
    assert len(commands) <= 2, f"at most two slash commands, found {len(commands)}"
    assert not list(root.glob("drift.yaml")), "the guard must not require a config file"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/guard/test_hooks.py tests/guard/test_gates.py::test_gate_g4_surface_stays_small -v`
Expected: FAIL — Hook-Dateien und Manifest fehlen

- [ ] **Step 3: Hook-Skripte schreiben**

Zuerst die gemeinsame Auflösung, damit die Hooks auch dann funktionieren, wenn `drift-guard` nicht
auf dem PATH des Hook-Prozesses liegt (pipx, venv, uv-Installationen unterscheiden sich).

`hooks/_guard_lib.sh`:

```bash
#!/usr/bin/env bash
# Shared helpers for the drift guard hooks. Sourced, never executed directly.

# Resolve the guard entry point: prefer the console script, fall back to the
# module. Prints nothing and returns 1 when neither is available.
guard_cmd() {
  if command -v drift-guard >/dev/null 2>&1; then
    echo "drift-guard"
    return 0
  fi
  if python3 -c "import drift.guard" >/dev/null 2>&1; then
    echo "python3 -m drift.guard"
    return 0
  fi
  return 1
}

# Extract tool_input.file_path from the hook payload on stdin.
guard_file_from_payload() {
  python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))
except Exception:
    print("")
' 2>/dev/null
}

guard_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}
```

`hooks/guard-pre-edit.sh`:

```bash
#!/usr/bin/env bash
# Claude Code PreToolUse(Write|Edit): brief the agent before it creates a NEW
# Python file. Never fails, never blocks.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

file="$(guard_file_from_payload)"
[ -z "$file" ] && exit 0
case "$file" in *.py) ;; *) exit 0 ;; esac

cmd="$(guard_cmd)" || exit 0
repo="$(guard_repo_root)"
rel="${file#"$repo"/}"

$cmd --repo "$repo" pre --file "$rel" 2>/dev/null || true
exit 0
```

`hooks/guard-post-edit.sh`:

```bash
#!/usr/bin/env bash
# Claude Code PostToolUse(Write|Edit): report duplicates and first-ever
# boundary crossings introduced by the edit that just happened.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

file="$(guard_file_from_payload)"
[ -z "$file" ] && exit 0
case "$file" in *.py) ;; *) exit 0 ;; esac

cmd="$(guard_cmd)" || exit 0
repo="$(guard_repo_root)"
rel="${file#"$repo"/}"

$cmd --repo "$repo" post --file "$rel" 2>/dev/null || true
exit 0
```

`hooks/guard-session-start.sh`:

```bash
#!/usr/bin/env bash
# Claude Code SessionStart: reset the session tally and make sure an index
# exists. The build runs detached so the session never waits for it.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

cmd="$(guard_cmd)" || exit 0
repo="$(guard_repo_root)"

if [ ! -f "$repo/.drift/index.db" ]; then
  ( $cmd --repo "$repo" build >/dev/null 2>&1 & ) || true
  echo "drift: building structural index in the background; guard active shortly."
  exit 0
fi

$cmd --repo "$repo" reset 2>/dev/null || true
echo "drift guard active: after each edit it reports symbols that already exist elsewhere and first-ever directory imports."
exit 0
```

`hooks/guard-stop.sh`:

```bash
#!/usr/bin/env bash
# Claude Code Stop: print what the guard caught during this session.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

cmd="$(guard_cmd)" || exit 0
$cmd --repo "$(guard_repo_root)" stats 2>/dev/null || true
exit 0
```

Ausführbar machen: `chmod +x hooks/guard-*.sh` (`_guard_lib.sh` wird nur gesourct, braucht kein x-Bit)

- [ ] **Step 4: Manifest und Slash-Commands schreiben**

`.claude-plugin/plugin.json`:

```json
{
  "name": "drift",
  "version": "3.0.0",
  "description": "Tells your coding agent when it is about to build something that already exists.",
  "author": { "name": "Mick Gottschalk", "email": "mick.gottsch@gmail.com" },
  "homepage": "https://github.com/mick-gsk/drift",
  "license": "MIT",
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-session-start.sh" }] }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-pre-edit.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-post-edit.sh" }]
      }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-stop.sh" }] }
    ]
  }
}
```

`.claude-plugin/marketplace.json`:

```json
{
  "name": "drift",
  "owner": { "name": "mick-gsk", "url": "https://github.com/mick-gsk" },
  "plugins": [
    {
      "name": "drift",
      "source": "./",
      "description": "Tells your coding agent when it is about to build something that already exists."
    }
  ]
}
```

`commands/drift-doctor.md`:

```markdown
---
description: Check that the drift guard is installed, indexed and answering.
---

Run `drift-guard doctor` in the repository root and show the output as a
checklist. If any line shows `[ ]`, run `drift-guard build` and show the
result, then run doctor again.
```

`commands/drift-stats.md`:

```markdown
---
description: Show what the drift guard caught in this session.
---

Run `drift-guard stats` in the repository root and show the output verbatim.
Report zero findings as zero — do not embellish.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/guard/test_hooks.py tests/guard/test_gates.py -v`
Expected: PASS

- [ ] **Step 6: Manuell im echten Claude Code verifizieren**

```bash
# im drift-Repo
/plugin marketplace add /Users/moritzbecker/drift
/plugin install drift@drift
```

Danach Claude Code neu starten, `/drift:doctor` ausführen (alle `[x]`), eine Python-Datei anlegen, die eine bestehende Funktion dupliziert, und prüfen, dass der Hinweis erscheint. Das Ergebnis dieser manuellen Prüfung als Kommentar in den Commit schreiben.

- [ ] **Step 7: Commit**

```bash
chmod +x hooks/guard-*.sh
git add .claude-plugin hooks commands tests/guard/test_hooks.py tests/guard/test_gates.py
git commit -m "feat(guard): ship drift as a Claude Code plugin with four hooks"
```

---

### Task 11: Gates G6 und G7, dann alle Gates in CI

**Files:**
- Modify: `tests/guard/test_gates.py` — G6 und G7 ergänzen
- Create: `.github/workflows/guard-gates.yml`

**Interfaces:**
- Consumes: alles Bisherige
- Produces: CI-Job `guard-gates`, der `scripts/gates/run_all_gates.py` ausführt

- [ ] **Step 1: G6- und G7-Tests schreiben**

An `tests/guard/test_gates.py` anhängen:

```python
INDEX_BUILD_BUDGET_S = 120.0
INCREMENTAL_BUDGET_S = 2.0


@pytest.mark.performance
def test_gate_g6_index_build_is_fast_enough():
    """G6: a full build of this repository must finish inside the budget."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    started = time.perf_counter()
    stats = build.build_full(repo_root)
    elapsed = time.perf_counter() - started

    assert stats["files"] > 0
    assert elapsed <= INDEX_BUILD_BUDGET_S, f"full build took {elapsed:.1f}s"

    started = time.perf_counter()
    build.update_file(repo_root, "src/drift/guard/lookup.py")
    incremental = time.perf_counter() - started

    assert incremental <= INCREMENTAL_BUDGET_S, f"incremental took {incremental:.2f}s"


def test_gate_g7_counter_only_counts_real_hits(sample_repo):
    """G7: the tally must move only when a lookup actually produced a hit."""
    build.build_full(sample_repo)
    report.reset_counter(sample_repo)
    conn = schema.connect(sample_repo)

    # A clean file: no hits, so the counter must not move.
    source = (sample_repo / "src" / "auth" / "session.py").read_text(encoding="utf-8")
    symbols, imports = extract.extract(source)
    clean_hits = lookup.find_duplicates(conn, "src/auth/session.py", symbols)
    clean_hits += lookup.find_novel_edges(conn, "src/auth/session.py", imports)
    for hit in clean_hits:
        report.bump(sample_repo, hit.kind)

    assert report.read_counter(sample_repo) == {"duplicate": 0, "boundary": 0}

    # A real duplicate: exactly one increment, no more.
    dup_symbols, _ = extract.extract("def validate_token(a, b):\n    return None\n")
    hits = lookup.find_duplicates(conn, "src/api/schemas.py", dup_symbols)
    for hit in hits:
        report.bump(sample_repo, hit.kind)

    assert report.read_counter(sample_repo) == {"duplicate": 1, "boundary": 0}
```

**Achtung:** `test_gate_g6_index_build_is_fast_enough` baut den Index des echten Repos und überschreibt damit `.drift/index.db`. Das ist gewollt (der Index ist ein Cache und in `.gitignore`). Sicherstellen, dass `.drift/` in `.gitignore` steht — falls nicht, Zeile `.drift/` ergänzen.

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/guard/test_gates.py -v`
Expected: alle PASS

- [ ] **Step 3: Sammel-Gate ausführen**

Run: `.venv/bin/python scripts/gates/run_all_gates.py`
Expected: `all gates passed`, Exit 0

- [ ] **Step 4: CI-Workflow schreiben**

`.github/workflows/guard-gates.yml`:

```yaml
name: guard-gates

on:
  pull_request:
    paths:
      - "src/drift/guard/**"
      - "hooks/**"
      - ".claude-plugin/**"
      - "commands/**"
      - "tests/guard/**"
      - "scripts/gates/**"
      - ".github/workflows/guard-gates.yml"
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  gates:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install package without extras
        run: python -m pip install -e . --no-deps
      - name: Install test tooling
        run: python -m pip install pytest pytest-timeout
      - name: Run all guard gates
        run: python scripts/gates/run_all_gates.py
```

Der Job installiert bewusst **ohne** Extras — das ist zugleich die Probe, dass der Guard ohne ML-Abhängigkeiten funktioniert.

- [ ] **Step 5: Commit**

```bash
git add tests/guard/test_gates.py .github/workflows/guard-gates.yml .gitignore
git commit -m "ci: run all guard gates on pull requests"
```

---

### Task 12: Ein Versprechen — README und Install-Gate (G5)

**Files:**
- Modify: `README.md` — neuer Kopf
- Create: `scripts/gates/measure_install.sh`
- Modify: `tests/guard/test_gates.py` — G5 ergänzen

**Interfaces:**
- Consumes: das fertige Plugin
- Produces: `measure_install.sh`, das die Zeit von Clean-Checkout bis `drift-guard doctor` grün misst

- [ ] **Step 1: Install-Messskript schreiben**

`scripts/gates/measure_install.sh`:

```bash
#!/usr/bin/env bash
# Gate G5: measure clean install to a working guard, in seconds.
set -euo pipefail

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

start="$(date +%s)"

python3 -m venv "$workdir/venv"
"$workdir/venv/bin/pip" install --quiet -e . --no-deps
"$workdir/venv/bin/pip" install --quiet click rich pyyaml pydantic gitpython networkx

cp -R tests/guard/fixtures/sample_repo "$workdir/repo"
"$workdir/venv/bin/drift-guard" --repo "$workdir/repo" build >/dev/null
"$workdir/venv/bin/drift-guard" --repo "$workdir/repo" doctor

end="$(date +%s)"
elapsed=$(( end - start ))
echo "install_to_first_value_seconds=$elapsed"
[ "$elapsed" -le 60 ] || { echo "G5 FAILED: $elapsed s > 60 s"; exit 1; }
echo "G5 passed"
```

Ausführbar machen: `chmod +x scripts/gates/measure_install.sh`

- [ ] **Step 2: Skript ausführen**

Run: `bash scripts/gates/measure_install.sh`
Expected: `G5 passed` und eine Sekundenzahl ≤ 60

Schlägt es fehl, ist fast immer `pip install` der Kostenpunkt — dann die Messung auf den Plugin-Pfad beschränken (`/plugin install` benötigt kein venv) und die Änderung im Skriptkopf begründen.

- [ ] **Step 3: README-Kopf neu schreiben**

Die ersten Zeilen von `README.md` (bis einschließlich des Blocks mit `pip install drift-analyzer`) ersetzen durch:

```markdown
# Drift

**Your agent is about to build it twice. Drift tells it first.**

Drift is a Claude Code plugin. After every edit your agent makes, it says one of two things —
or, most of the time, nothing at all:

- `validate_token` already exists as `validate_token` in `src/auth/tokens.py:44`
- first import from `src/api/` into `src/db/` anywhere in this repository

No configuration. No LLM. No network. One SQLite index, two questions, under 150 ms per edit.

```bash
/plugin marketplace add mick-gsk/drift
/plugin install drift@drift
```

Then restart Claude Code and run `/drift:doctor`.

`/drift:stats` shows what it caught this session.
```

Der Rest des bisherigen README bleibt darunter als Abschnitt „CLI (advanced)" erhalten — nichts löschen, nur nach unten verschieben und mit einer Überschrift versehen.

- [ ] **Step 4: G5-Test ergänzen**

An `tests/guard/test_gates.py` anhängen:

```python
def test_gate_g5_install_script_exists_and_is_executable():
    """G5: the install measurement must be a runnable script, not a claim."""
    import os

    script = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "gates" / "measure_install.sh"

    assert script.exists()
    assert os.access(script, os.X_OK), "measure_install.sh must be executable"


def test_readme_leads_with_the_plugin_promise():
    """The front page must sell one promise, and it must be the guard."""
    root = pathlib.Path(__file__).resolve().parents[2]
    head = (root / "README.md").read_text(encoding="utf-8").split("\n")[:30]
    text = "\n".join(head)

    assert "/plugin install drift@drift" in text
    assert "build it twice" in text.lower()
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/guard/test_gates.py -v`
Expected: alle PASS

- [ ] **Step 6: Commit**

```bash
chmod +x scripts/gates/measure_install.sh
git add README.md scripts/gates/measure_install.sh tests/guard/test_gates.py
git commit -m "docs: lead with one promise and gate install time at 60 seconds"
```

---

### Task 13: Abschluss — alle Gates, Baseline-Vergleich, Handover-Notiz

**Files:**
- Modify: `benchmark_results/guard_baseline.json` — Abschlussmessung
- Create: `docs/superpowers/plans/2026-07-29-drift-agent-guard-RESULT.md`

**Interfaces:**
- Consumes: alles
- Produces: ein Dokument, das jede Gate-Zahl mit Vorher/Nachher zeigt

- [ ] **Step 1: Alle Gates laufen lassen**

```bash
.venv/bin/python scripts/gates/run_all_gates.py
bash scripts/gates/measure_install.sh
```

Beide Ausgaben vollständig kopieren — sie kommen ins Ergebnisdokument.

- [ ] **Step 2: Vollständige Testsuite laufen lassen**

Run: `.venv/bin/python -m pytest tests/guard -v`
Expected: alle PASS

Danach zur Sicherheit die bestehende Suite auf Regressionen prüfen:
Run: `.venv/bin/python -m pytest tests -x -q -m "not slow"`
Expected: keine neuen Fehlschläge gegenüber dem Stand vor Task 1. Gibt es welche, beheben — der Plan durfte nichts Bestehendes brechen.

- [ ] **Step 3: Ergebnisdokument schreiben**

`docs/superpowers/plans/2026-07-29-drift-agent-guard-RESULT.md` mit dieser Tabelle, ausgefüllt mit **gemessenen** Werten (keine Schätzungen):

```markdown
# Drift Agent Guard — Ergebnis

| Gate | Schwelle | Vorher | Nachher | Status |
|---|---|---|---|---|
| G1 Latenz `pre` p95 | ≤ 150 ms | — (existierte nicht) | … | … |
| G1 Latenz `post` p95 | ≤ 150 ms | — | … | … |
| G2 Import-Hygiene | 0 schwere Module | 13 (über `drift.cli`) | … | … |
| G3 Recall auf Ground Truth | ≥ 90 % | 0 % (Vertrag war leer) | … | … |
| G3 Falschmeldungen auf sauberen Dateien | 0 | 0 | … | … |
| G4 Oberfläche | ≤ 2 Tools, ≤ 2 Commands | 47 CLI-Commands | … | … |
| G5 Install → Guard aktiv | ≤ 60 s | nicht existent | … | … |
| G6 Index-Bau (drift-Repo) | ≤ 120 s | 214–462 s pro Ein-Datei-Prüfung | … | … |
| G7 Zähler-Ehrlichkeit | Test grün | nicht existent | … | … |

## Referenzmessungen

`benchmark_results/guard_baseline.json`

## Was bewusst offen blieb

- Outcome-Validierung des drift-Scores (unverändert offen, siehe Spec §7)
- Reduktion der 47 CLI-Commands und 60 CI-Workflows (nicht Teil dieses Vorhabens)
- Weitere Plattformen (Cursor, Copilot, Codex)
```

- [ ] **Step 4: Commit**

```bash
git add benchmark_results/guard_baseline.json docs/superpowers/plans/2026-07-29-drift-agent-guard-RESULT.md
git commit -m "docs: record measured gate results for the drift agent guard"
```

---

## Anhang: Reihenfolge und Abbruchkriterien

| Task | Liefert | Abbruch, wenn |
|---|---|---|
| 1 | Messharness + Baseline | — |
| 2 | Ground-Truth-Korpus | — |
| 3–7 | Index und Lookups | — |
| 8 | Schlanke CLI, G2 | G2 lässt sich nicht erfüllen, ohne Bestehendes zu ändern → Spec-Änderung mit dem Nutzer klären |
| 9 | G1, G3 scharf | G1 auch nach den drei Optimierungsschritten unerreichbar → Budget dokumentiert anheben, nicht heimlich |
| 10 | Das Plugin, G4 | Manuelle Verifikation in Claude Code schlägt fehl → nicht weitergehen, erst reparieren |
| 11 | G6, G7, CI | — |
| 12 | Ein Versprechen, G5 | — |
| 13 | Nachweis | Ein Gate rot → nicht als fertig melden |

**Die eine Regel für diese Umsetzung:** Jede Zahl in jedem Bericht stammt aus einem Kommando, dessen Output im Terminal stand. Keine geschätzten, gerundeten oder erinnerten Werte.
