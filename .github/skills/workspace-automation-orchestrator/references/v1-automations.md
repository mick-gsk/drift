# V1 Automationskatalog

## Ziel

V1 automatisiert nur lokale, risikoarme und bestehende Repo-Workflows.

## Automationskandidaten

1. `quality_fast_lane`
- Trigger: wiederholter Bedarf nach schneller Verifikation
- Ablauf:
  - `make test-fast`
  - bei Erfolg optional `make gate-check COMMIT_TYPE=fix`
- Auto-Run: erlaubt

2. `pre_commit_guard`
- Trigger: wiederholte Gate-Fehler vor Commit/Push
- Ablauf:
  - `make gate-check COMMIT_TYPE=<feat|fix|chore|signal>`
  - bei signal-/ingestion-/output-Aenderungen `make audit-diff`
- Auto-Run: erlaubt

3. `full_confidence_run`
- Trigger: Abschluss-/Freigabestatus vor groesseren Aenderungen
- Ablauf:
  - `make check`
- Auto-Run: erlaubt, wenn keine langlaufenden konkurrierenden Jobs aktiv sind

4. `changelog_snippet_assist`
- Trigger: wiederkehrender CHANGELOG-Eintrag pro Commit-Typ
- Ablauf:
  - `make changelog-entry COMMIT_TYPE=<...> MSG='...'`
- Auto-Run: erlaubt

5. `workflow_discovery`
- Trigger: unklare Wahl passender Scripts
- Ablauf:
  - `make catalog`
- Auto-Run: erlaubt

## Nicht in V1

- Remote-Aktionen (`git push`, PR/Issue write)
- autonome Branch-/Merge-Operationen
- externe Workflow-Tools (Zapier/Make/n8n)

## Erfolgskriterien fuer V1

- weniger manuelle Wiederholung bei gleichbleibender Gate-Disziplin
- keine Verletzung der Hard-Block-Regeln
- nachvollziehbarer Abschlussreport bei jeder Ausfuehrung
