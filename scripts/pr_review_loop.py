#!/usr/bin/env python3
"""Thin CLI entry point wrapper for drift pr-loop.

Usage:
    python scripts/pr_review_loop.py <PR_NUMBER> [options]

Delegates to `drift pr-loop` Click command.
"""

from __future__ import annotations


def main() -> None:
    from drift.pr_loop._cmd import pr_loop_cmd

    pr_loop_cmd(standalone_mode=True)


if __name__ == "__main__":
    main()
