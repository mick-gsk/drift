---
id: ADR-002
status: proposed
date: 2026-04-02
supersedes:
---

# ADR-002: Differenzierte export-context-Formate (instructions/prompt/raw)

## Kontext

Issue #80 zeigt, dass die drei angebotenen Formate von `drift export-context` bislang inhaltlich fast identisch waren. Das erzeugt eine Scheinauswahl ohne klaren Mehrwert und reduziert die Einfuehrbarkeit fuer Agent-Integrationen.

## Entscheidung

Die Formate werden funktional klar getrennt:

- `instructions`: bleibt das ausfuehrliche, menschenlesbare Markdown mit DO NOT/INSTEAD, Kategorien und Dateihinweisen.
- `prompt`: wird auf eine kompakte, token-effiziente Regelliste verdichtet (einzeilige Regeln im Format `DO_NOT -> INSTEAD`).
- `raw`: wird auf machine-readable JSON umgestellt (`drift-negative-context-v1`) inklusive Metadaten und strukturierter Item-Felder.

Nicht Bestandteil dieser Entscheidung:

- neue Signale oder Scoring-Logik
- Aenderungen an Ingestion-Pfaden
- Aenderungen an MCP-Anreicherungslogik

## Begründung

Die Trennung verbessert unmittelbar den Nutzwert pro Einsatzkontext:

- Prompt-Kontexte profitieren von geringerem Token-Budget.
- Automations-Workflows koennen `raw` stabil parsen statt Markdown zu scrapen.
- Bestehende Instructions-Workflows bleiben lesbar und handlungsorientiert.

Alternativen:

- Formate beibehalten: verworfen wegen fehlender Differenzierung.
- Formate reduzieren auf eins: verworfen, da unterschiedliche Konsumenten real existieren.

## Konsequenzen

- `raw` ist nicht mehr Markdown, sondern JSON.
- Tests fuer `prompt` und `raw` muessen semantisch angepasst werden.
- CLI-Hilfetext muss die neue Bedeutung von `raw` klar benennen.

## Validierung

- Unit-Tests in `tests/test_negative_context_export.py` pruefen:
  - kompakte Prompt-Regeln,
  - JSON-Gueltigkeit und Schema-Basis fuer `raw`,
  - unveraenderte Gruppierungs-/Trunkierungslogik im `instructions`-Format.
- Lernzyklus-Ergebnis (Policy §10): **unklar** bis externe Integrationsrueckmeldung vorliegt.
