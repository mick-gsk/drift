# vulture_whitelist.py
# Unused-code whitelist for vulture.
# Symbols here are dynamically called (Click callbacks, Pydantic fields, etc.)
# and would otherwise be reported as "unused" by vulture.
#
# Auto-managed by .github/workflows/dead-code-loop.yml — do not edit by hand.
# New entries are added automatically when dead-code-loop detects new findings.
# To manually whitelist a symbol, add it to [tool.vulture] ignore_names in pyproject.toml.

# Pre-existing dynamic symbols (duplicated from pyproject.toml ignore_names for reference):
model_config  # noqa: F821  Pydantic model config field
as_dict  # noqa: F821  Pydantic serialisation helper
