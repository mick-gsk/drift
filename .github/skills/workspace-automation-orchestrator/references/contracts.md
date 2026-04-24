# Contracts

## Detection Contract

Der Skill erkennt Automationskandidaten aus wiederkehrenden, regelbasierten Schritten mit niedriger Entscheidungsnotwendigkeit.

### Kandidatensignale

- gleicher oder aehnlicher Befehl tritt mehrfach in kurzer Zeit auf
- gleiche Ablaufsequenz tritt wiederholt auf
- gleiche Fehlerklasse erzeugt wiederholt denselben manuellen Fix
- hoher Kontextwechsel fuer einen sonst mechanischen Ablauf

### Prioritaetsmodell

`priority = frequency_score * effort_score * consistency_gain / risk_factor`

- `frequency_score`: 1 bis 5
- `effort_score`: 1 bis 5
- `consistency_gain`: 1 bis 5
- `risk_factor`: 1 bis 5

Auto-Ausfuehrung nur wenn `priority >= 8` und Safety-Checks erfolgreich sind.

## Safety Contract

### Hard Blocks

Niemals automatisch:

- `git push` oder andere Remote-Write-Operationen
- automatisches Posten in Issues/PRs
- destructive Git-Aktionen (`git reset --hard`, `git checkout --`)

### Allowlist (V1)

- `make test-fast`
- `make check`
- `make gate-check COMMIT_TYPE=<...>`
- `make audit-diff`
- `make changelog-entry COMMIT_TYPE=<...> MSG='...'`
- `make catalog`
- zielgerichtete lokale Testkommandos

### Escalation

Bei jeder Aktion ausserhalb der Allowlist:

1. blockieren
2. Grund nennen
3. sichere Alternative vorschlagen
4. explizite User-Freigabe einholen

## Execution Contract

### Workflow

1. Discovery
2. Scoring
3. Safety-Gate je Aktion
4. Execute (Safe-Scopes) oder Escalate
5. Abschlussreport

### Pflichtreport

- `detected_repetitions`
- `candidate_scores`
- `auto_executed`
- `blocked_actions`
- `manual_approvals_needed`
- `next_best_automations`
