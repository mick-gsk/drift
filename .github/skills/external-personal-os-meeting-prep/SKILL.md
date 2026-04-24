---
name: meeting-prep
description: Prepare contact dossiers before meetings. Use when you need to research someone before a meeting, create a contact card in Obsidian, or check upcoming meetings that lack a briefing.
when_to_use: Use when a meeting is coming up, when you need background on a new contact, or during morning heartbeat to check calendar for unbriefed meetings.
---

# Meeting Prep — Contact Dossier

## What This Skill Does
1. Finds upcoming meetings in the calendar
2. Searches the web for information about participants
3. Creates/updates contact cards in Obsidian (if configured)
4. Prepares a concise briefing

## Rules

1. **2 hours before the meeting** — prepare dossiers for all external participants
2. **Check Obsidian first** — don't duplicate existing files
3. **Append, don't overwrite** — if file exists, add new info
4. **After the meeting** — add a link to the note in the daily log
5. **Call summaries** — reformat for Obsidian but preserve the original

### Meeting Note Format (with summary)

```markdown
# Meeting: {Participant} — {Topic}
**Date:** {date}

---

## Key Topics
{reformatted structure}

## Next Steps
{action items from summary}

---

## 📝 Original Summary

> {original text as-is}
```

## Quick Start

### Check calendar for meetings without briefings
```bash
gog calendar events --days 7
```

### Check existing contacts
```bash
ls "${OBSIDIAN_VAULT}/88- Contacts/" | grep -i "{name}"
```
If file exists — read and update as needed.

### Research a person
1. Web search (LinkedIn, news, publications)
2. Create contact file from template
3. Send briefing to messaging platform

## Information Sources

### ⚡ Primary: web_search (Perplexity)
```
web_search("{Full Name} position company LinkedIn experience")
web_search("{Full Name} news interviews publications")
web_search("{Full Name} controversy legal") — for due diligence
```

### Priority Order
1. **LinkedIn** — positions, experience, education
2. **News** — media mentions, achievements, controversies
3. **Publications** — articles, blogs, op-eds
4. **Social** — Twitter/X, personal blog
5. **Companies** — orgs they've worked at
6. **Legal** — court filings if relevant (finance, politics)

### Web Fetch for specific URLs
```
web_fetch("https://linkedin.com/in/username")
```

## Contact Card Template

See [references/contact-template.md](references/contact-template.md)

## Briefing Template

```markdown
## 🎯 Briefing: {Name} — {Meeting Date}

**Who they are:**
- {Title} at {Company}
- {Key fact}

**Background:**
- {2-3 career highlights}

**Interesting:**
- {Unusual facts, hobbies, public positions}

**⚠️ Watch out for:**
- {Red flags if any}

**Possible topics:**
- {Shared interests, overlap points}

📋 Full dossier: {link to Obsidian note}
```

## Automation

### Cron (optional)
Daily calendar check at 08:00 for meetings in the next 48h:
```
text: "Check the calendar for the next 48 hours. For each external meeting without a dossier, prepare one."
schedule: "0 8 * * *"
```

### HEARTBEAT.md trigger
```markdown
### 📅 Meeting Prep (morning)
- Check today's and tomorrow's calendar
- For new contacts — build dossier
```

## Dossier Depth

### Minimum (5 min)
- Full name, title, company
- LinkedIn profile URL
- 1-2 news mentions

### Standard (15 min)
- Full profile (career, education)
- Public activity
- Contact info
- 3-5 sources

### Deep (30+ min) — for high-stakes meetings
- Detailed career timeline
- Analysis of writings and talks
- Network (who knows them, who introduced you)
- Due diligence (legal, controversies if relevant)
- Interest analysis (hobbies, social media patterns)

## Obsidian Integration

Configure via environment or `config.json`:
```json
{
  "obsidian_vault": "${OBSIDIAN_VAULT}",
  "contacts_path": "88- Contacts",
  "meetings_path": "88- Contacts/Meetings"
}
```

### File Naming
- Contact: `{Last Name First Name}.md`
- Meeting: `{YYYY-MM-DD} {Name} - {Topic}.md`
