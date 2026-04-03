# Installation

## From PyPI

We recommend using the quiet mode (`-q`) to suppress verbose dependency resolution output:

```bash
pip install -q drift-analyzer
```

The `-q` flag provides a cleaner experience by hiding transitive dependency chains. If you prefer to see all dependencies, use:

```bash
pip install drift-analyzer
```

## From Source

```bash
git clone https://github.com/mick-gsk/drift.git
cd drift
pip install -e ".[dev]"
```

## Optional Extras

```bash
# TypeScript/TSX support
pip install -q drift-analyzer[typescript]

# Embedding-based duplicate detection
pip install -q drift-analyzer[embeddings]

# All extras
pip install -q drift-analyzer[all]
```

## Requirements

- Python 3.11+
- Git (for history-based signals)
