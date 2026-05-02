# Data Model: CLI Load Reduction

## Entity: CommandCapabilityArea
- Purpose: Gruppiert thematisch zusammengehoerige CLI-Kommandos fuer zielorientierte Navigation.
- Fields:
  - id (string, stable, machine-friendly)
  - title (string, user-facing)
  - purpose (string, kurze Erkllaerung in Nicht-Entwickler-Sprache)
  - command_refs (list[string], referenziert bestehende Commands)
  - priority (int, steuert Reihenfolge in Help-Ausgabe)
- Validation Rules:
  - id muss eindeutig sein
  - command_refs darf nicht leer sein
  - priority muss >= 0 sein

## Entity: EntryPath
- Purpose: Definiert einen empfohlenen Einstieg fuer ein konkretes Nutzerziel.
- Fields:
  - id (string)
  - goal_text (string)
  - steps (list[EntryStep])
  - audience (enum: new_user, returning_user)
- Validation Rules:
  - mind. 1 Schritt vorhanden
  - jeder Schritt referenziert gueltigen Command oder Subcommand

## Entity: EntryStep
- Purpose: Einzelner Schritt in einem Einstiegspfad.
- Fields:
  - order (int)
  - action_text (string)
  - command_example (string)
- Validation Rules:
  - Reihenfolge innerhalb eines EntryPath eindeutig
  - command_example darf nicht leer sein

## Entity: HelpSection
- Purpose: Renderbare Sektion in CLI-Help (Uebersicht, Kategorien, Deep-Dive-Hinweise).
- Fields:
  - key (string)
  - heading (string)
  - body_lines (list[string])
  - next_hint (string | null)
- Validation Rules:
  - heading nicht leer
  - body_lines nicht leer

## Relationships
- Ein CommandCapabilityArea enthaelt viele Command-Referenzen.
- Ein EntryPath enthaelt viele EntrySteps.
- HelpSection kann EntryPath- und CommandCapabilityArea-Informationen verdichten.

## State Transitions
- Draft Design -> Reviewed Design: Validierungsregeln und Mapping vollstaendig.
- Reviewed Design -> Implemented Rendering: Help-Ausgabe wird aus Modellen generiert.
- Implemented Rendering -> Contract Verified: CLI-Contract-Tests bestehen fuer Struktur und Kompatibilitaet.