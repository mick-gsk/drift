---
id: ADR-101
status: proposed
date: 2026-05-01
supersedes:
---

# ADR-101: VS Code Extension Architecture for vscode-drift

## Kontext

Der Drift-MCP-Server (`drift mcp --serve`) läuft bereits als stdio-Prozess und
ist in `.vscode/mcp.json` konfiguriert. Alle Analyse-Logik liegt serverseitig.
Eine VS-Code-Extension soll als dünne Konsumentenschicht auf MCP aufsetzen und
dem Entwickler Inline-Findings (Diagnostics), einen Score-Status-Bar und einen
Nudge-nach-Edit bereitstellen — ohne eigene Analyse-Logik.

Offene Entscheidungen:
1. **MCP-Client-Bibliothek:** Offizielles `@modelcontextprotocol/sdk` vs. eigener
   JSON-RPC-Wrapper vs. VS-Code-nativer MCP-Client (noch nicht stabil öffentlich).
2. **Mono-Repo vs. separates Repo:** Extension in `extensions/vscode-drift/` (hier)
   vs. eigenständiges Repository.
3. **Versionsmatrix:** Welche Drift-Versionen unterstützt die Extension?
4. **Diagnostic-Severity-Mapping:** Wie werden Drift-Severities auf VS-Code-Levels gemapped?

## Entscheidung

### MCP-Client-Bibliothek
**Gewählt: `@modelcontextprotocol/sdk` (offiziell, TypeScript-first).**

Die SDK stellt `Client` und `StdioClientTransport` bereit. Der Transport spawnt den
Drift-MCP-Server als Kindprozess und kommuniziert über stdin/stdout per JSON-RPC.
Das SDK ist TypeScript-first, wird aktiv gepflegt und ist die Referenzimplementierung
des MCP-Protokolls.

Verworfen:
- *Eigener JSON-RPC-Wrapper:* Unnötiger Wartungsaufwand; das Protokoll enthält
  Handshake, Capability-Negotiation und Framing-Details, die das SDK korrekt
  implementiert.
- *VS-Code-nativer MCP-Client:* Noch kein stabiles öffentliches API in
  VS-Code-Extensions.

### Mono-Repo vs. separates Repo
**Gewählt: Mono-Repo in `extensions/vscode-drift/`.**

Die Extension ist eng an den Drift-MCP-Server gekoppelt (Tool-Signaturen,
Session-Protokoll). Ein gemeinsames Repository vereinfacht Änderungs-Kohärenz,
Versionierung und CI. Die Aufteilung in ein separates Repo ist als spätere
Option offen (nach Marketplace-Release).

### Versionsmatrix
Die Extension kommuniziert ausschließlich über das MCP-Protokoll. Sie setzt
kein spezifisches Drift-Python-Paket voraus, sofern der MCP-Server korrekt
startet. Getestete Mindestversion: Drift ≥ 2.38.0 (erster Release mit stabilem
MCP-Interface). Die Extension dokumentiert die Anforderung in ihrer README.

### Diagnostic-Severity-Mapping

| Drift-Severity | VS-Code-DiagnosticSeverity |
|---------------|---------------------------|
| `high`        | `Error`                   |
| `medium`      | `Warning`                 |
| `low`         | `Information`             |
| (kein Wert)   | `Hint`                    |

Dieses Mapping ist konsistent mit der Drift-Output-Konvention und der
Erwartungshaltung gängiger Linter-Extensions in VS Code.

## Begründung

- Das SDK minimiert eigenen Protokoll-Code auf nahezu null.
- Das Mono-Repo reduziert Release-Friction in der Beta-Phase erheblich.
- Das Severity-Mapping orientiert sich an etablierten VS-Code-Linter-Konventionen
  (ESLint, Pylance), sodass Nutzer keine neue mentale Skala lernen müssen.

## Konsequenzen

- `package.json` enthält `@modelcontextprotocol/sdk` als Produktionsabhängigkeit.
- Die Extension spawnt den MCP-Server als Kindprozess; der Python-Pfad ist
  konfigurierbar (`drift.pythonPath`).
- Bei fehlendem Python oder Drift zeigt die Extension einen klaren
  Installations-Hinweis statt einer stummen Fehlfunktion.
- Ein Marketplace-Release erfordert einen eigenen Publisher-Account und ist
  nicht Teil dieser ADR.

## Validierung

- Lokaler `vsce package`-Lauf ohne Fehler.
- Extension aktiviert im VS-Code-Testhost ohne Runtime-Exception.
- Drift-Findings erscheinen als Diagnostics nach `Drift: Analyze Workspace`.
- `Drift: Nudge Current File` zeigt Direction-Notification nach Edit.
- Fehlerpfad bei nicht gefundenem Python liefert actionable Fehlermeldung.
