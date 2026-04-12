---
description: "Nutze diese Kurz-Instruction, wenn schnell geklaert werden muss, ob im Drift-Repo ein manueller Release-Befehl noetig ist. Kurzregel: Conventional Commits verwenden, Release macht CI."
---

# Release Automation

> **Vollständige Dokumentation:** siehe `drift-release-automation.instructions.md` (gleicher Scope).

Diese Datei ist absichtlich knapp und dient nur als Reminder.

**Kurzregel:** Conventional Commits (`feat:`, `fix:`, `BREAKING:`) verwenden — CI übernimmt Version, Tag, Release und PyPI.
Kein manueller Release-Befehl nötig. Lokaler Fallback nur bei CI-Ausfall: `python scripts/release_automation.py --full-release`.

## See Also

- Release Workflow: `.github/workflows/release.yml`
- PSR Configuration: `pyproject.toml` → `[tool.semantic_release]`
- Detailed Skill: `.github/skills/drift-release/SKILL.md`
