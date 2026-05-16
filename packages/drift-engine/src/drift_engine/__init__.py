"""drift-engine: signal detection, scoring, and ingestion engine for drift-analyzer.

This package contains the core analysis engine:
- signals/    — 24 detection signals (BaseSignal subclasses)
- scoring/    — weighted composite score engine
- ingestion/  — file discovery, AST/git parsing
- pipeline    — analysis pipeline orchestration
- analyzer    — high-level analyzer entry point
"""
