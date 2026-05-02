# Contract: CLI Help Navigation

## Scope
Oeffentliche CLI-Hilfeoberflaeche fuer `drift --help` im Rahmen der kognitiven Lastreduktion.

## Public Contract

### C-001 Start-Section
- `drift --help` MUSS eine prominente Einstiegsektion enthalten.
- Die Sektion MUSS mindestens einen klaren, ausfuehrbaren Startpfad zeigen.

### C-002 Capability Grouping
- Kommandos MUESSEN in nachvollziehbaren Aufgabenbereichen dargestellt werden.
- Jeder Bereich MUSS eine kurze Zweckbeschreibung in nutzerorientierter Sprache enthalten.

### C-003 Navigation Hand-off
- Die Uebersicht MUSS einen expliziten Weg in tiefere Hilfe bieten (z. B. Bereich -> Detailhilfe).

### C-004 Backward Compatibility
- Bestehende CLI-Aufrufe bleiben funktional erhalten.
- Neue Help-Struktur darf bestehende Automationen nicht brechen.

### C-005 Stability for Testing
- Reihenfolge und Benennung der Hauptsektionen MUESSEN stabil genug fuer Contract-Tests sein.

## Verification Mapping
- C-001, C-002, C-003: `tests/help_nav/test_help_nav_contract.py`
- C-004: `tests/help_nav/test_help_nav_integration.py`
- C-005: `tests/help_nav/test_help_nav_contract.py` (section-order assertions)

## Non-goals
- Keine Umbenennung/Entfernung bestehender Kommandos in dieser Phase.
- Keine adaptive, telemetry-gesteuerte Personalisierung der Help-Reihenfolge.