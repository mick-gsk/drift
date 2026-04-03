---
name: "Drift Onboarding"
agent: agent
description: "Testet die Erstnutzer-Erfahrung bei Drift-Adoption in einem neuen Repository: Init, Config, First-Run-Erfolg und Time-to-Value für neue Teams oder Contributors."
---

# Drift Onboarding

Du evaluierst, wie schnell ein neuer Maintainer, Contributor oder ein Team mit Drift in einem bisher nicht konfigurierten Repository Nutzen erzielen kann.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing.md`
- **Verwandte Prompts:** `drift-agent-workflow-test.prompt.md` (Phase 7b testet Onboarding breiter)
- **Onboarding-Doku:** `DEVELOPER.md`, `CONTRIBUTING.md`

## Arbeitsmodus

- Denke wie ein fähiger Neueinsteiger ohne verstecktes Maintainer-Wissen.
- Unterscheide verwirrende Produktverhalten von normalem Erstnutzer-Lernaufwand.
- Reduziere jedes Onboarding-Problem auf den ersten fehlenden Hinweis, der den User entblocken würde.
- Bevorzuge konkrete Friktions-Logs gegenüber allgemeinen Eindrücken.
- Fasse Time-to-Value in Kommandos, Entscheidungen und Unsicherheitspunkten zusammen.

## Ziel

Bestimme, ob das Drift-Onboarding verständlich, reibungsarm und robust genug für Erstnutzer ist.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Wie einfach ist es, Drift in einem frischen Repo oder einer Sandbox zu initialisieren?
- Sind Config-Workflows verständlich und debugbar?
- Kann ein erstes nützliches Ergebnis schnell erreicht werden?
- Welche Onboarding-Lücken verlangsamen die Adoption am meisten?

## Arbeitsregeln

- Bewerte aus der Perspektive eines neuen Users, nicht eines bestehenden Maintainers.
- Bevorzuge eine Sandbox oder einen isolierten Repo-Pfad für schreibintensive Onboarding-Kommandos.
- Zähle verwirrende Voraussetzungen und stillschweigende Annahmen als Onboarding-Defekte.
- Protokolliere den ersten Punkt, an dem ein neuer User wahrscheinlich zögern würde.
- Miss Time-to-Value am Erreichen eines sinnvollen ersten Ergebnisses, nicht am bloßen Erstellen von Dateien.

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Ergebnis-Bewertung** pro Schritt: `pass` / `review` / `fail`
- **Risiko-Level** pro Friktionspunkt: `low` / `medium` / `high` / `critical`

## Artefakte

Erstelle Artefakte unter `work_artifacts/onboarding_<YYYY-MM-DD>/`:

1. `sandbox/`
2. `init_output.txt`
3. `config_validate.txt`
4. `config_show.txt`
5. `first_run_notes.md`
6. `onboarding_report.md`

## Workflow

### Phase 0: Neueinsteiger-Perspektive einnehmen

Nimm an, du hast kein repo-spezifisches Drift-Wissen außer dem, was CLI und generierte Dateien liefern.

Dokumentiere:
- Was ist das offensichtliche erste Kommando?
- Welche Voraussetzungen sind sichtbar oder versteckt?
- Was müsste ein Neueinsteiger wissen, bevor er fortfährt?
- Gibt es Hinweise auf `DEVELOPER.md` oder `CONTRIBUTING.md`?

### Phase 1: In Sandbox initialisieren

Erstelle eine Sandbox und initialisiere Drift:

```bash
mkdir -p work_artifacts/onboarding_<YYYY-MM-DD>/sandbox
cd work_artifacts/onboarding_<YYYY-MM-DD>/sandbox
git init
echo "def example(): pass" > main.py
git add . && git commit -m "init"
drift init --full --repo .
```

Bewerte:
- Sind die generierten Dateien verständlich?
- Sind die Defaults sinnvoll?
- Erklärt die Kommandoausgabe, was als nächstes zu tun ist?

**Generierte-Assets-Rubrik** — jedes erzeugte Artefakt bewerten nach:
1. **Verständlich?** — Kann ein Neueinsteiger ohne Doku verstehen, was die Datei bewirkt?
2. **Vollständig?** — Enthält die Datei alle nötigen Felder/Optionen für den Startfall?
3. **Korrekt?** — Spiegeln die Defaults das erwartete Verhalten wider?

### Phase 2: Config validieren und inspizieren

```bash
drift config validate --repo <SANDBOX>
drift config show --repo <SANDBOX>
```

Bewerte:
- Sind Config-Probleme leicht diagnostizierbar?
- Ist die angezeigte Config tatsächlich nützlich für Menschen?
- Ist der nächste Schritt nach Config klar?

### Phase 3: Ersten Nutzen erreichen

Vom initialisierten Zustand aus den natürlichsten ersten Analyseschritt ausführen:

```bash
drift analyze --repo <SANDBOX> --format json
```

Dies ist das Mindest-Kommando für das erste sinnvolle Ergebnis.

Wenn das Sandbox-Repo zu klein für aussagekräftige Findings ist, wiederhole mit dem echten Repository:

```bash
drift scan --max-findings 5 --response-detail concise
```

Protokolliere:
- Wie viele Kommandos waren nötig, bevor ein sinnvolles Ergebnis erschien?
- Wo würde ein Neueinsteiger wahrscheinlich Hilfe brauchen?
- Fühlt sich das Produkt früh genug vertrauenswürdig an?

### Phase 4: Report erstellen

```markdown
# Drift Onboarding Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [REPO-NAME oder SANDBOX]

## Time-to-Value

| Schritt | Kommando | Ergebnis | Bewertung | Friktion | Anmerkungen |
|---------|----------|----------|-----------|----------|-------------|

## Onboarding-Friktionspunkte

| Schritt | Problem | Risiko-Level | Warum es Adoption verlangsamt | Lösungsvorschlag |
|---------|---------|-------------|-------------------------------|------------------|

## Generierte Assets

| Datei/Ausgabe | Verständlich? | Vollständig? | Korrekt? | Anmerkungen |
|---------------|---------------|-------------|----------|-------------|

## First-Run-Vertrauensbewertung

[Konkretes Urteil basierend auf Evidenz — nicht nur subjektiver Eindruck.
Kriterien: Keine unerwarteten Fehler? Ausgabe konsistent? Nächster Schritt klar?]

## Prioritäre Verbesserungen

1. [...]
2. [...]
3. [...]
```

## Entscheidungsregel

Wenn ein Neueinsteiger externes Maintainer-Wissen braucht, um erfolgreich zu sein, zählt das als Onboarding-Friktion — selbst wenn der Workflow am Ende funktioniert.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues erstellen gemäß `.github/prompts/_partials/issue-filing.md`.

**Prompt-Kürzel für Titel:** `onboarding`

### Issues erstellen für

- Verwirrendes oder unvollständiges `init`-Verhalten
- Config-Validierung oder -Anzeige, die schwer diagnostizierbar sind
- Fehlende Next-Step-Guidance nach Setup
- Defaults oder generierte Dateien, die den Ersterfolg erschweren

### Keine Issues erstellen für

- Rein lokale Umgebungsprobleme außerhalb von Drifts Verantwortung
- Subjektive Stilpräferenzen ohne Onboarding-Auswirkung
- Duplikate bereits existierender Issues
