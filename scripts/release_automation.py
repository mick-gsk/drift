#!/usr/bin/env python3
"""Simple Release Automation for Drift Analyzer."""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"


def run_tests() -> bool:
    """Run quick tests."""
    print("\n▶ Running quick tests...")
    try:
        subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--tb=short",
                "--ignore=tests/test_smoke.py",
                "-q",
                "--maxfail=1",
            ],
            cwd=ROOT,
            check=True,
        )
        print("✓ Tests passed")
        return True
    except subprocess.CalledProcessError:
        print("✗ Tests failed")
        return False


def get_latest_version() -> tuple[int, int, int]:
    """Get latest version from git tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*.*.*"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        tags = sorted([t for t in result.stdout.strip().split("\n") if t])
        if tags:
            match = re.match(r"v(\d+)\.(\d+)\.(\d+)", tags[-1])
            if match:
                major, minor, patch = match.groups()
                return (int(major), int(minor), int(patch))
    except Exception:
        pass
    return (0, 1, 0)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Drift Release Automation")
    parser.add_argument("--full-release", action="store_true", help="Full release workflow")
    parser.add_argument("--calc-version", action="store_true", help="Calculate version only")
    parser.add_argument("--skip-tests", action="store_true", help="Skip tests")

    args = parser.parse_args()

    print("=" * 60)
    print("Drift Release Automation")
    print("=" * 60)

    # Run tests if not skipped
    if not args.skip_tests and (args.full_release or args.calc_version) and not run_tests():
        print("\n✗ Tests failed. Aborting release.")
        return 1

    # Calculate next version
    current = get_latest_version()
    next_patch = current[2] + 1
    next_version = f"v{current[0]}.{current[1]}.{next_patch}"

    print(f"\n▶ Next version: {next_version}")

    if not args.full_release:
        print("(Use --full-release to perform actual release)")
        return 0

    # Full release: update files, commit, tag, push
    version_no_v = next_version.lstrip("v")

    try:
        # Update pyproject.toml
        pyproject_content = PYPROJECT.read_text("utf-8")
        pyproject_content = re.sub(
            r'version = "[^"]+"',
            f'version = "{version_no_v}"',
            pyproject_content,
            count=1,
        )
        PYPROJECT.write_text(pyproject_content, "utf-8")
        print(f"✓ Updated pyproject.toml: {version_no_v}")

        # Update CHANGELOG
        today = datetime.now().strftime("%Y-%m-%d")
        new_section = (
            f"\n## [{version_no_v}] — {today}\n"
            f"\n### Release\n- Version {version_no_v}\n"
        )
        changelog_content = ""
        if CHANGELOG.exists():
            changelog_content = CHANGELOG.read_text("utf-8")

        CHANGELOG.write_text(new_section + changelog_content, "utf-8")
        print(f"✓ Updated CHANGELOG.md: {version_no_v}")

        print("\n▶ Creating release commit and tag...")
        subprocess.run(
            ["git", "add", "pyproject.toml", "CHANGELOG.md"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"chore: Release {version_no_v}"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["git", "tag", "-a", next_version, "-m", f"Release {next_version}"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["git", "push", "origin", "master", "--tags"],
            cwd=ROOT,
            check=True,
        )

        print(f"✓ Committed: chore: Release {version_no_v}")
        print(f"✓ Tagged: {next_version}")
        print("✓ Pushed to GitHub")
        print(f"\n✅ Release {next_version} complete!")
        print("   → GitHub Actions will publish to PyPI")

        return 0

    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
