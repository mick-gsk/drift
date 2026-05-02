# ruff: noqa: F401, F403
import drift_config as _target

__path__ = _target.__path__
from drift_config import *
from drift_config import _default_includes as _default_includes

# Explicit re-exports for mypy
from drift_config import detect_repo_profile as detect_repo_profile
