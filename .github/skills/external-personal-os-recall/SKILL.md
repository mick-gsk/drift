---
name: recall
version: "1.0.0"
description: "Load context from past sessions. Three modes: temporal (what did I work on yesterday/last week), topic (semantic search across sessions and notes), and graph (visual map of session-file relationships). Every recall ends with One Thing — the single highest-leverage next action."
when_to_use: "Use when user says: 'recall', 'what did we work on', 'what was I doing yesterday/last week', 'load context about X', 'prime context', 'remember when we', 'session history', 'what have I done on this project', 'show me the graph', or any temporal/historical query about past work."
argument-hint: "[yesterday|today|last week|this week|TOPIC|graph DATE_EXPR]"
author: "Personal OS Skills (inspired by ArtemXTech/personal-os-skills)"
---

# Recall

> *Your agent forgets between sessions. Recall fixes that.*

Three modes: **temporal** (date-based), **topic** (semantic search), **graph** (visual map). Every recall ends with **One Thing** — a concrete, specific next action synthesized from what you find.

---

## Modes

### 1. Temporal — What were you working on?

```
/recall yesterday
/recall last week
/recall 2026-03-28
/recall this week
/recall last 3 days
```

Scans `memory/YYYY-MM-DD.md` and `memory/chat-log-YYYY-MM-DD.jsonl` files chronologically. Shows a timeline of sessions with topics, decisions made, and tasks in progress.

**What it shows:**
- Sessions list (time, topic, key decisions)
- Tasks that were in progress → which are done, which are stuck
- Decisions made and why
- Open loops that weren't closed

### 2. Topic — What do you know about X?

```
/recall authentication
/recall meeting with Bayram
/recall MoltNet architecture
/recall voice cloning
```

Searches across:
- `memory/` daily files
- `MEMORY.md` long-term memory
- `SESSION-STATE.md`
- Any notes in the workspace

Uses keyword + semantic matching. Returns relevant excerpts with dates.

### 3. Graph — Visualize your work streams

```
/recall graph yesterday
/recall graph last week
/recall graph last 3 days
```

Generates an interactive HTML visualization:
- Sessions as nodes, colored by day
- Files touched as connected nodes
- Clusters reveal related work streams
- Shared files show cross-session dependencies

Output: `memory/recall-graph-YYYY-MM-DD.html` — opens in browser.

---

## The One Thing

Every recall ends with synthesis:

> *Based on what has momentum, what's blocked, and what's closest to done — here's the single highest-leverage action right now:*
>
> **[Specific, actionable, not generic]**

Not "work on your project." More like "The auth flow has been blocked for 3 days — unblock it by making the decision about OAuth vs API keys you've been deferring."

---

## How It Works

### Step-by-step execution

**Temporal query:**
```bash
# 1. Find relevant memory files
ls ~/[workspace]/memory/YYYY-MM-DD.md  # today and requested range

# 2. Read them chronologically
cat memory/2026-03-28.md memory/2026-03-29.md ...

# 3. Also check SESSION-STATE.md for current hot context
cat memory/SESSION-STATE.md

# 4. Build timeline
# 5. Synthesize One Thing
```

**Topic query:**
```bash
# 1. Search memory files for topic
grep -r "TOPIC" memory/ --include="*.md" -l

# 2. If QMD is available (faster, semantic):
qmd search "TOPIC" -n 10

# 3. Read matched sections
# 4. Synthesize what's known + One Thing
```

**Graph query:**
```bash
# 1. Parse memory files for file references and decisions
# 2. Build adjacency data
# 3. Generate HTML with D3.js visualization
python3 ${CLAUDE_SKILL_DIR}/scripts/generate-graph.py --days 7 --output memory/recall-graph.html
# 4. Open in browser or share link
```

---

## Configuration

No configuration required. Works with any workspace that has `memory/` files.

**Optional — better search with QMD:**
```bash
# Install QMD for semantic search
npm install -g @qmd/cli
qmd index memory/ --collection sessions
```

**Optional — richer graph with file tracking:**
Add to your `AGENTS.md`:
```
When touching important files, log them to memory/YYYY-MM-DD.md:
  - Touched: path/to/file.md
```

---

## Examples

**"What was I doing last week?"**
```
📅 Last week (Mar 24–30):

Mon Mar 24: Voice cloning setup — installed Chatterbox, tested on DGX
Tue Mar 25: LanguageMirror backend — /clone-voice endpoint working
Wed Mar 26: Blocked on Russian TTS (CosyVoice failed), pivoted to English MVP
Thu Mar 27: Voxtral announcement — saved notes, compared to ElevenLabs
Fri Mar 28: Content pipeline — built preflight-check.sh, integrated with Moltbook

🔄 In progress: LanguageMirror end-to-end test (Pron)
✅ Done: Chatterbox, preflight-check
❌ Blocked: Russian TTS, Google Auth

⚡ One Thing: The LanguageMirror test has been queued for Pron for 3 days — check if it's done or unblock it.
```

**"What do I know about the MoltNet architecture?"**
```
📚 Found 8 references across 12 sessions (Mar 15 – Mar 31):

[2026-03-15] Decided: Node 1 Strasbourg as primary, Proxmox VE
[2026-03-18] Router deployed at /opt/moltnet/router/router.js
[2026-03-22] MoltWallet vs MoltPay distinction documented
[2026-03-28] Node 2 Singapore planned (Ryzen 9950X €299)

Key decision: Multi-tenant VPS marketplace, Telegram-first

⚡ One Thing: Node 2 Singapore has been "planned" for 2 weeks with no action — decide: this month or defer to Q3?
```

---

## Upgrade Path

| Setup | What you get |
|-------|-------------|
| Just `memory/` files | Temporal recall, basic topic search |
| + QMD installed | Semantic topic search, faster |
| + file tracking in AGENTS.md | Richer graph with file relationships |
| + SESSION-STATE.md protocol | Real-time hot context always available |

Start simple. Add as needed.

---

## See Also

- `evolutionary-model` — why memory persistence matters
- `onboarding` — set up your memory foundation first
- ArtemXTech's original `recall` skill for Claude Code + Obsidian workflows
