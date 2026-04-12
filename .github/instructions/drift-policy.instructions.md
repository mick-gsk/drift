---
applyTo: "**"
description: "Nutze diese Instruction immer als verbindlichen Gate-Wrapper fuer Drift-Arbeit. Sie enthaelt das Pflicht-Gate, das Kompaktformat fuer Trivialaufgaben und die Verweise auf die autoritative POLICY.md."
---

# Drift — Policy (bindend für alle Dateioperationen)

`POLICY.md` im Workspace-Root ist die **Single Source of Truth** fuer Produkt-, Priorisierungs- und Risiko-Regeln.
Diese Instruction wiederholt die Policy nicht, sondern liefert das operative Gate-Format fuer Agenten.

## PFLICHT-GATE: Zulässigkeitsprüfung — immer zuerst ausführen und ausgeben

Vor jeder Umsetzung dieses Format sichtbar ausgeben:

```
### Drift Policy Gate
- Aufgabe: [Kurzbeschreibung in einem Satz]
- Zulassungskriterium erfüllt: [JA / NEIN] → [Unsicherheit / Signal / Glaubwürdigkeit / Handlungsfähigkeit / Trend / Einführbarkeit]
- Ausschlusskriterium ausgelöst: [JA / NEIN] → [falls JA: welches]
- Roadmap-Phase: [1 / 2 / 3 / 4] — blockiert durch höhere Phase: [JA / NEIN]
- Betrifft Signal/Architektur (§18): [JA / NEIN] → falls JA: Audit-Artefakte aktualisiert: [welche]
- Entscheidung: [ZULÄSSIG / ABBRUCH]
- Begründung: [ein Satz]
```

Bei **ABBRUCH**: keine Umsetzung, stattdessen Erklärung + Gegenvorschlag.
Eine `ZULÄSSIG`-Entscheidung ist nur gültig, wenn das erfüllte Kriterium konkret zur Aufgabe passt. Generische Defaults ohne Aufgabenbezug sind ungültig.

Für **rein mechanische, verhaltensneutrale Trivialaufgaben** wie `fix: typo`, `docs: wording`, `chore: lockfile refresh` oder `test: fixture rename` ist dieses Kompaktformat zulässig:

```
### Drift Policy Gate
- Trivialtask: JA
- Zulässig: JA → rein mechanisch, ohne Verhaltens-, Policy-, Architektur- oder Signaleffekt
```

Nicht trivial sind insbesondere Änderungen an Policy, Instructions, Prompts, Skills, Agents, Signalen, Output-Formaten, CLI-Verhalten, Tests mit Verhaltensabsicherung oder Architekturgrenzen.

---

## Autoritative Verweise in POLICY.md

- Zulassung und Ausschluss: `POLICY.md` §8 und §9
- Priorisierung und Reihenfolge: `POLICY.md` §6 und §7
- Befund-Qualität: `POLICY.md` §13
- Unklare Entscheidungen: `POLICY.md` §16
- Risiko-Audit-Pflichten: `POLICY.md` §18

## Zusatzhinweise fuer Agenten

- Bei Kollision zwischen dieser Datei und `POLICY.md` gilt immer `POLICY.md`.
- Bei Signalarbeit oder Architekturgrenzen zusaetzlich `.github/instructions/drift-push-gates.instructions.md` und die passenden Audit-/ADR-Workflows lesen.
- Diese Datei ist absichtlich knapp, damit das Gate immer im Kontext bleibt, ohne die gesamte Policy zu duplizieren.
