"""Drift — Detect architectural erosion from AI-generated code."""

from __future__ import annotations

import os

# Pin the OpenMP runtime to one thread before anything can import a library
# that starts it. Drift parallelises at the file level with its own thread
# pool; when an OpenMP-backed extension (torch and scikit-learn arrive with
# the `embeddings` extra) is then called from those worker threads, libomp
# faults with SIGSEGV in __kmp_suspend_initialize_thread. Nesting OpenMP
# inside an existing pool buys nothing here and costs a hard crash, so the
# outer level keeps the parallelism. `setdefault` leaves an explicit choice
# by the caller untouched.
for _omp_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_omp_var, "1")

from importlib.metadata import PackageNotFoundError, version  # noqa: E402


def _resolve_version() -> str:
    """Resolve installed package version for CLI/output metadata."""
    for package_name in ("drift-analyzer", "drift"):
        try:
            return version(package_name)
        except PackageNotFoundError:
            continue
    return "0.0.0"


__version__ = _resolve_version()
