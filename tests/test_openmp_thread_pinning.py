"""Importing drift must pin the OpenMP runtime before anything can start it.

Regression guard for a SIGSEGV that took down `drift self` and
`drift analyze --path <dir>` entirely, and with them the pre-push hook that
calls the latter. The crash report pointed at libomp:

    EXC_BAD_ACCESS (SIGSEGV) KERN_INVALID_ADDRESS at 0x580
    libomp.dylib  __kmp_suspend_initialize_thread
    libomp.dylib  __kmp_fork_barrier
    libomp.dylib  __kmp_launch_worker

Drift parallelises at the file level with its own thread pool. When an
OpenMP-backed extension (torch and scikit-learn arrive with the `embeddings`
extra) is called from inside those workers, the nested OpenMP fork faults.
Pinning the runtime to a single thread removes the nesting; the outer pool
keeps the parallelism.

The pinning only works if it happens before the native library is imported,
which is why it lives at the top of `drift/__init__.py` rather than in the CLI.
"""

from __future__ import annotations

import os
import subprocess
import sys

THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


def test_importing_drift_pins_the_openmp_runtime():
    probe = (
        "import drift, os\n"
        f"print(','.join(os.environ.get(v, '<unset>') for v in {THREAD_VARS!r}))\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in THREAD_VARS}

    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True, env=env
    )

    assert result.stdout.strip() == "1,1,1"


def test_an_explicit_setting_is_left_alone():
    """A caller who asked for four threads gets four, crash risk and all."""
    probe = "import drift, os\nprint(os.environ['OMP_NUM_THREADS'])\n"
    env = dict(os.environ, OMP_NUM_THREADS="4")

    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True, env=env
    )

    assert result.stdout.strip() == "4"


def test_pinning_happens_before_the_first_submodule_import():
    """Order matters: a library that already started OpenMP ignores the variable."""
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "src" / "drift" / "__init__.py"
    ).read_text(encoding="utf-8")

    pin_at = source.index("OMP_NUM_THREADS")
    first_metadata_import = source.index("from importlib.metadata")

    assert pin_at < first_metadata_import, (
        "the OpenMP pin must come before every other import in drift/__init__.py"
    )
