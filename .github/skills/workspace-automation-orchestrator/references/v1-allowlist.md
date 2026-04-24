# V1 Allowlist And Denylist

Diese Datei definiert die erlaubten und verbotenen Aktionstypen fuer den Skill workspace-automation-orchestrator.

## Allowed Auto-Run Commands

Nur lokale und risikoarme Orchestrierung:

- make catalog
- make gate-check COMMIT_TYPE=feat
- make gate-check COMMIT_TYPE=fix
- make gate-check COMMIT_TYPE=chore
- make gate-check COMMIT_TYPE=signal
- make audit-diff
- make test-fast
- python scripts/gate_check.py --commit-type feat
- python scripts/gate_check.py --commit-type fix
- python scripts/gate_check.py --commit-type chore
- python scripts/gate_check.py --commit-type signal
- python scripts/risk_audit_diff.py

## Conditional Commands

Nur nach expliziter User-Bestaetigung oder klarer Anforderung:

- make check
- make changelog-entry COMMIT_TYPE=<...> MSG='...'

## Denied Auto-Run Commands

Nie automatisch ausfuehren:

- git push
- git reset --hard
- git checkout -- <path>
- git rebase --interactive
- jede Aktion, die Issue- oder PR-Kommentare postet
- jede Aktion mit Remote-Write-Seiteneffekt

## Escalation Template

Wenn eine Aktion nicht erlaubt ist:

1. Blockieren
2. Grund nennen (Denylist oder ausserhalb Safe-Scope)
3. Sichere Alternative anbieten
4. Explizite Freigabe anfordern
