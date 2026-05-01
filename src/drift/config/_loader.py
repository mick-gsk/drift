"""Thin backward-compat wrapper -- real implementation lives in drift_config._loader."""
from drift_config._loader import *  # noqa: F401, F403
from drift_config._loader import (
    DriftConfig as DriftConfig,
)
from drift_config._loader import (
    PrLoopConfig as PrLoopConfig,
)
from drift_config._loader import (
    _default_includes as _default_includes,
)
from drift_config._loader import (
    build_config_json_schema as build_config_json_schema,
)
from drift_config._loader import (
    detect_repo_profile as detect_repo_profile,
)
