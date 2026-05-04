"""Plain-language message catalog for all Drift signals.

Maps each ``signal_id`` to audience-friendly templates in multiple languages.
Every template supports ``str.format_map()`` substitution with Finding fields:

    {file}    — file_path as posix string (or "unbekannt" / "unknown")
    {symbol}  — symbol name (or "unbekannt" / "unknown")
    {line}    — start_line (or "?")
    {impact}  — impact score as percentage string (e.g. "75 %")

The catalog is intentionally a flat dict — no i18n framework, no gettext.
Community can extend by adding language keys.
"""
# ruff: noqa: E501

from __future__ import annotations

from typing import TypedDict


class PlainTemplate(TypedDict):
    """Single plain-language template for one signal in one language."""

    title: str
    description: str
    impact: str
    action: str


# signal_id → { lang_code → PlainTemplate }
PLAIN_CATALOG: dict[str, dict[str, PlainTemplate]] = {
    # ── structural_risk ───────────────────────────────────────────────
    "pattern_fragmentation": {
        "de": {
            "title": "Uneinheitlicher Code-Aufbau",
            "description": "In {file} gibt es Code-Abschnitte, die ähnlich aussehen, aber unterschiedlich gebaut sind. Das macht Änderungen fehleranfällig.",
            "impact": "Wenn du etwas änderst, vergisst du leicht eine der Varianten — und erzeugst einen Fehler.",
            "action": "Bringe die ähnlichen Stellen auf ein einheitliches Muster.",
        },
        "en": {
            "title": "Inconsistent code structure",
            "description": "In {file}, similar code sections are built differently. This makes changes error-prone.",
            "impact": "When you change one variant, you may forget another — introducing bugs.",
            "action": "Unify the similar sections into one consistent pattern.",
        },
    },
    "mutant_duplicate": {
        "de": {
            "title": "Fast-identische Code-Kopien",
            "description": "Die Funktion {symbol} in {file} ist fast identisch mit einer anderen Funktion. Solche Kopien laufen mit der Zeit auseinander.",
            "impact": "Wenn du einen Fehler in einer Kopie behebst, bleibt er in der anderen bestehen.",
            "action": "Fasse die beiden Funktionen zu einer zusammen.",
        },
        "en": {
            "title": "Near-identical code copies",
            "description": "The function {symbol} in {file} is nearly identical to another function. Such copies diverge over time.",
            "impact": "Fixing a bug in one copy leaves the other broken.",
            "action": "Merge the two functions into one.",
        },
    },
    "temporal_volatility": {
        "de": {
            "title": "Häufig geänderter Code",
            "description": "{file} wird ungewöhnlich oft geändert. Das deutet auf instabilen oder schlecht strukturierten Code hin.",
            "impact": "Jede Änderung an dieser Stelle birgt ein höheres Risiko für neue Fehler.",
            "action": "Prüfe ob die Datei zu viele Aufgaben gleichzeitig erledigt.",
        },
        "en": {
            "title": "Frequently changed code",
            "description": "{file} is changed unusually often, indicating unstable or poorly structured code.",
            "impact": "Every change here carries a higher risk of introducing new bugs.",
            "action": "Check if this file handles too many responsibilities.",
        },
    },
    "system_misalignment": {
        "de": {
            "title": "Inkonsistenz zwischen Teilsystemen",
            "description": "In {file} passen die Strukturen nicht zum Rest des Systems. Das führt zu Überraschungen bei Änderungen.",
            "impact": "Änderungen in einem Teil können unerwartete Auswirkungen in einem anderen haben.",
            "action": "Gleiche die Struktur an die Konventionen des restlichen Systems an.",
        },
        "en": {
            "title": "Inconsistency across subsystems",
            "description": "In {file}, structures don't match the rest of the system, causing surprises during changes.",
            "impact": "Changes in one part may cause unexpected effects in another.",
            "action": "Align the structure with the rest of the system's conventions.",
        },
    },
    "test_polarity_deficit": {
        "de": {
            "title": "Fehlende Negativ-Tests",
            "description": "Für {symbol} in {file} gibt es nur Tests, die den Erfolgsfall prüfen — aber keine Tests für Fehlerfälle.",
            "impact": "Deine App funktioniert im Normalfall, aber stürzt ab oder verhält sich falsch wenn etwas schiefgeht.",
            "action": "Schreibe Tests, die prüfen was passiert wenn ungültige Eingaben kommen.",
        },
        "en": {
            "title": "Missing negative tests",
            "description": "For {symbol} in {file}, only success cases are tested — no tests for failure scenarios.",
            "impact": "Your app works normally but crashes or misbehaves when something goes wrong.",
            "action": "Write tests that verify behavior with invalid inputs.",
        },
    },
    "bypass_accumulation": {
        "de": {
            "title": "Zu viele Ausnahme-Markierungen",
            "description": "In {file} gibt es viele Stellen, an denen Prüfungen absichtlich übersprungen werden (z.B. # noqa, type: ignore).",
            "impact": "Die übersprungenen Prüfungen könnten echte Fehler verbergen.",
            "action": "Gehe die Markierungen einzeln durch und behebe die eigentlichen Ursachen.",
        },
        "en": {
            "title": "Too many bypass markers",
            "description": "In {file}, many checks are intentionally skipped (e.g. # noqa, type: ignore).",
            "impact": "Skipped checks may hide real bugs.",
            "action": "Review each marker and fix the underlying issues.",
        },
    },
    "exception_contract_drift": {
        "de": {
            "title": "Uneinheitliche Fehlerbehandlung",
            "description": "In {file} werden Fehler unterschiedlich behandelt — mal wird abgefangen, mal nicht, mal mit verschiedenen Strategien.",
            "impact": "Manche Fehler werden verschluckt, andere stürzen die App ab — unvorhersehbar.",
            "action": "Einige dich auf eine einheitliche Fehlerbehandlung im gesamten Projekt.",
        },
        "en": {
            "title": "Inconsistent error handling",
            "description": "In {file}, errors are handled differently — sometimes caught, sometimes not, with varying strategies.",
            "impact": "Some errors are silently swallowed, others crash the app — unpredictably.",
            "action": "Agree on a consistent error handling strategy for the project.",
        },
    },
    "ts_architecture": {
        "de": {
            "title": "TypeScript-Architekturproblem",
            "description": "In {file} gibt es TypeScript-spezifische Strukturprobleme.",
            "impact": "Der Code wird schwerer wartbar und kann bei Typ-Änderungen unerwartete Fehler verursachen.",
            "action": "Prüfe die TypeScript-Architektur und bringe sie in Einklang mit den Projekt-Konventionen.",
        },
        "en": {
            "title": "TypeScript architecture problem",
            "description": "In {file}, there are TypeScript-specific structural issues.",
            "impact": "The code becomes harder to maintain and may cause unexpected errors during type changes.",
            "action": "Review the TypeScript architecture and align it with project conventions.",
        },
    },
    # ── architecture_boundary ─────────────────────────────────────────
    "architecture_violation": {
        "de": {
            "title": "Schicht-Verletzung",
            "description": "{file} greift auf Code zu, der eigentlich in einer anderen Schicht liegt. Das macht die Struktur fragil.",
            "impact": "Änderungen an einer Stelle ziehen unerwartete Änderungen an vielen anderen Stellen nach sich.",
            "action": "Verschiebe den Zugriff so, dass er über die vorgesehene Schnittstelle läuft.",
        },
        "en": {
            "title": "Layer violation",
            "description": "{file} accesses code from a different architecture layer, making the structure fragile.",
            "impact": "Changes in one place trigger unexpected changes in many other places.",
            "action": "Route the access through the intended interface.",
        },
    },
    "circular_import": {
        "de": {
            "title": "Zirkuläre Abhängigkeit",
            "description": "{file} und andere Dateien importieren sich gegenseitig im Kreis. Das kann zu Startfehlern oder unerwartetem Verhalten führen.",
            "impact": "Deine App könnte beim Starten abstürzen oder sich unvorhersehbar verhalten.",
            "action": "Durchbreche den Kreis, indem du gemeinsamen Code in eine eigene Datei auslagerst.",
        },
        "en": {
            "title": "Circular dependency",
            "description": "{file} and other files import each other in a circle, which can cause startup failures.",
            "impact": "Your app might crash at startup or behave unpredictably.",
            "action": "Break the circle by extracting shared code into a separate file.",
        },
    },
    "co_change_coupling": {
        "de": {
            "title": "Versteckte Kopplung",
            "description": "{file} muss immer zusammen mit anderen Dateien geändert werden — ein Zeichen für versteckte Abhängigkeiten.",
            "impact": "Wenn du eine Datei änderst aber die andere vergisst, entsteht ein Fehler.",
            "action": "Prüfe ob die Dateien zusammengelegt oder besser entkoppelt werden können.",
        },
        "en": {
            "title": "Hidden coupling",
            "description": "{file} always needs to change together with other files — a sign of hidden dependencies.",
            "impact": "Changing one file but forgetting the other introduces bugs.",
            "action": "Check if the files can be merged or better decoupled.",
        },
    },
    "cohesion_deficit": {
        "de": {
            "title": "Datei macht zu viel auf einmal",
            "description": "{file} enthält Code, der viele verschiedene Dinge tut. Das macht die Datei schwer verständlich.",
            "impact": "Jede Änderung erfordert Verständnis des gesamten Inhalts — Fehler schleichen sich leichter ein.",
            "action": "Teile die Datei in kleinere, thematisch zusammenhängende Module auf.",
        },
        "en": {
            "title": "File does too many things",
            "description": "{file} contains code doing many different things, making it hard to understand.",
            "impact": "Every change requires understanding the entire file — bugs sneak in more easily.",
            "action": "Split the file into smaller, focused modules.",
        },
    },
    "fan_out_explosion": {
        "de": {
            "title": "Zu viele Abhängigkeiten",
            "description": "{file} hängt von sehr vielen anderen Dateien ab. Das macht sie anfällig für Änderungen überall im Projekt.",
            "impact": "Änderungen an fast jeder anderen Datei können diese Datei kaputtmachen.",
            "action": "Reduziere die Anzahl der Abhängigkeiten oder führe eine Zwischenschicht ein.",
        },
        "en": {
            "title": "Too many dependencies",
            "description": "{file} depends on very many other files, making it vulnerable to changes anywhere.",
            "impact": "Changes to almost any other file can break this one.",
            "action": "Reduce dependencies or introduce an intermediary layer.",
        },
    },
    # ── style_hygiene ─────────────────────────────────────────────────
    "naming_contract_violation": {
        "de": {
            "title": "Inkonsistente Benennung",
            "description": "{symbol} in {file} folgt nicht der Benennungs-Konvention des Projekts.",
            "impact": "Andere Entwickler (oder dein zukünftiges Ich) finden den Code schwerer verständlich.",
            "action": "Benenne {symbol} gemäß der Projekt-Konvention um.",
        },
        "en": {
            "title": "Inconsistent naming",
            "description": "{symbol} in {file} doesn't follow the project's naming convention.",
            "impact": "Other developers (or your future self) will find the code harder to understand.",
            "action": "Rename {symbol} according to the project convention.",
        },
    },
    "doc_impl_drift": {
        "de": {
            "title": "Dokumentation stimmt nicht mit Code überein",
            "description": "Die Dokumentation von {symbol} in {file} beschreibt etwas anderes als der Code tatsächlich tut.",
            "impact": "Wer sich auf die Dokumentation verlässt, wird in die Irre geführt.",
            "action": "Aktualisiere die Dokumentation, damit sie zum aktuellen Code passt.",
        },
        "en": {
            "title": "Documentation doesn't match code",
            "description": "The documentation for {symbol} in {file} describes something different from what the code does.",
            "impact": "Anyone relying on the documentation will be misled.",
            "action": "Update the documentation to match the current code.",
        },
    },
    "explainability_deficit": {
        "de": {
            "title": "Komplexer Code ohne Erklärung",
            "description": "{symbol} in {file} ist komplex, aber nicht dokumentiert. Ohne Erklärung ist unklar, warum der Code so geschrieben ist.",
            "impact": "Niemand (auch du nicht in 3 Monaten) versteht, was dieser Code tut oder warum.",
            "action": "Füge eine Erklärung hinzu, die den Zweck und die Logik beschreibt.",
        },
        "en": {
            "title": "Complex code without explanation",
            "description": "{symbol} in {file} is complex but undocumented. Without explanation, it's unclear why it's written this way.",
            "impact": "Nobody (including you in 3 months) will understand what this code does or why.",
            "action": "Add documentation explaining the purpose and logic.",
        },
    },
    "broad_exception_monoculture": {
        "de": {
            "title": "Zu grobe Fehlerbehandlung",
            "description": "In {file} werden alle Fehler gleich behandelt — egal ob es ein Netzwerk-Timeout oder ein Programmierfehler ist.",
            "impact": "Echte Fehler werden verschluckt. Deine App tut so als wäre alles in Ordnung, obwohl etwas schiefgelaufen ist.",
            "action": "Fange nur die Fehler ab, die du erwartest und behandeln kannst.",
        },
        "en": {
            "title": "Too broad error handling",
            "description": "In {file}, all errors are handled the same — whether it's a network timeout or a programming bug.",
            "impact": "Real errors are silently swallowed. Your app pretends everything is fine when it's not.",
            "action": "Only catch errors you expect and can handle.",
        },
    },
    "guard_clause_deficit": {
        "de": {
            "title": "Fehlende Eingabe-Prüfungen",
            "description": "{symbol} in {file} prüft nicht, ob die Eingaben gültig sind, bevor es weiterarbeitet.",
            "impact": "Deine App stürzt ab oder verhält sich falsch, wenn jemand eine ungültige oder leere Eingabe macht.",
            "action": "Füge am Anfang der Funktion Prüfungen hinzu, die ungültige Eingaben frühzeitig abfangen.",
        },
        "en": {
            "title": "Missing input validation",
            "description": "{symbol} in {file} doesn't check if inputs are valid before proceeding.",
            "impact": "Your app crashes or misbehaves when someone provides invalid or empty input.",
            "action": "Add checks at the start of the function to catch invalid inputs early.",
        },
    },
    "dead_code_accumulation": {
        "de": {
            "title": "Ungenutzter Code",
            "description": "In {file} gibt es Code, der nie ausgeführt wird.",
            "impact": "Der ungenutzte Code macht die Datei unübersichtlich und kann Verwirrung stiften.",
            "action": "Lösche den ungenutzten Code — er ist nur Ballast.",
        },
        "en": {
            "title": "Unused code",
            "description": "In {file}, there's code that is never executed.",
            "impact": "Unused code clutters the file and can cause confusion.",
            "action": "Delete the unused code — it's just dead weight.",
        },
    },
    "cognitive_complexity": {
        "de": {
            "title": "Zu verschachtelter Code",
            "description": "{symbol} in {file} hat zu viele Ebenen von Bedingungen und Schleifen. Das macht den Code schwer nachvollziehbar.",
            "impact": "Fehler entstehen leicht, weil niemand alle Verzweigungen im Kopf behalten kann.",
            "action": "Vereinfache die Funktion — extrahiere Teile in eigene Funktionen.",
        },
        "en": {
            "title": "Overly nested code",
            "description": "{symbol} in {file} has too many levels of conditions and loops, making it hard to follow.",
            "impact": "Bugs arise easily because nobody can keep track of all branches.",
            "action": "Simplify the function — extract parts into separate functions.",
        },
    },
    # ── security ──────────────────────────────────────────────────────
    "missing_authorization": {
        "de": {
            "title": "Fehlende Zugriffskontrolle",
            "description": "{symbol} in {file} kann von jedem aufgerufen werden — es gibt keine Prüfung, ob der Nutzer dazu berechtigt ist.",
            "impact": "Unbefugte können auf Daten oder Funktionen zugreifen, die eigentlich geschützt sein sollten.",
            "action": "Füge eine Berechtigungsprüfung hinzu, bevor die Funktion ausgeführt wird.",
        },
        "en": {
            "title": "Missing access control",
            "description": "{symbol} in {file} can be called by anyone — there's no check whether the user is authorized.",
            "impact": "Unauthorized users can access data or functions that should be protected.",
            "action": "Add an authorization check before the function executes.",
        },
    },
    "insecure_default": {
        "de": {
            "title": "Unsichere Standardeinstellung",
            "description": "In {file} ist eine Einstellung standardmäßig unsicher konfiguriert.",
            "impact": "Deine App ist im Auslieferungszustand angreifbar, wenn niemand die Einstellung ändert.",
            "action": "Ändere den Standard auf eine sichere Konfiguration.",
        },
        "en": {
            "title": "Insecure default setting",
            "description": "In {file}, a setting is configured insecurely by default.",
            "impact": "Your app is vulnerable out of the box if nobody changes the setting.",
            "action": "Change the default to a secure configuration.",
        },
    },
    "hardcoded_secret": {
        "de": {
            "title": "Passwort oder Schlüssel im Code",
            "description": "In {file} steht ein Passwort, API-Schlüssel oder anderes Geheimnis direkt im Quellcode.",
            "impact": "Jeder der den Code sieht, kann das Geheimnis lesen und missbrauchen.",
            "action": "Verschiebe das Geheimnis in eine Umgebungsvariable oder einen Secret-Manager.",
        },
        "en": {
            "title": "Password or key in code",
            "description": "In {file}, a password, API key, or other secret is written directly in the source code.",
            "impact": "Anyone who sees the code can read and misuse the secret.",
            "action": "Move the secret to an environment variable or a secret manager.",
        },
    },
    # ── ai_quality ────────────────────────────────────────────────────
    "phantom_reference": {
        "de": {
            "title": "Verweis auf nicht existierenden Code",
            "description": "In {file} wird eine Funktion oder Klasse verwendet, die gar nicht existiert — wahrscheinlich von einer KI erfunden.",
            "impact": "Deine App stürzt ab, sobald diese Stelle aufgerufen wird.",
            "action": "Ersetze den Verweis durch eine tatsächlich existierende Funktion.",
        },
        "en": {
            "title": "Reference to non-existent code",
            "description": "In {file}, a function or class is used that doesn't exist — likely hallucinated by an AI.",
            "impact": "Your app crashes when this code path is reached.",
            "action": "Replace the reference with an actually existing function.",
        },
    },
    # ── typescript_quality ────────────────────────────────────────────
    "type_safety_bypass": {
        "de": {
            "title": "Typ-Sicherheit umgangen",
            "description": "In {file} wird die Typ-Prüfung absichtlich umgangen (z.B. mit 'as any' oder '@ts-ignore').",
            "impact": "Typ-Fehler werden nicht erkannt und können zur Laufzeit zu Abstürzen führen.",
            "action": "Entferne die Umgehung und korrigiere den eigentlichen Typ-Fehler.",
        },
        "en": {
            "title": "Type safety bypassed",
            "description": "In {file}, type checking is intentionally bypassed (e.g. with 'as any' or '@ts-ignore').",
            "impact": "Type errors go undetected and can cause crashes at runtime.",
            "action": "Remove the bypass and fix the underlying type error.",
        },
    },
}


# ---------------------------------------------------------------------------
# Fallback template for unknown / plugin signals
# ---------------------------------------------------------------------------

FALLBACK_TEMPLATES: dict[str, PlainTemplate] = {
    "de": {
        "title": "Code-Problem erkannt",
        "description": "In {file} wurde ein strukturelles Problem erkannt ({signal_type}).",
        "impact": "Dieses Problem kann die Wartbarkeit oder Zuverlässigkeit deiner App beeinträchtigen.",
        "action": "Prüfe die betroffene Stelle und behebe das Problem.",
    },
    "en": {
        "title": "Code problem detected",
        "description": "A structural problem was detected in {file} ({signal_type}).",
        "impact": "This problem may affect the maintainability or reliability of your app.",
        "action": "Review the affected location and fix the problem.",
    },
}
