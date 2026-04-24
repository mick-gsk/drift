---
name: content-creator
description: Generate social media posts and long-form content in a consistent authorial voice. Use when writing posts for Telegram channels, blogs, or social media in a specific owner-defined style.
when_to_use: Use when generating posts for a personal Telegram channel, blog, or social account; when writing content in the owner's voice; or when maintaining stylistic consistency across publications.
---

# Content Creator — Authorial Voice Generation

A skill for generating posts and content in your defined authorial style.

## When to Use
- Generating posts for a personal Telegram channel or blog
- Writing content in the owner's voice
- Maintaining stylistic consistency across publications

---

## Configuration

Customize your style by editing `config.json`:

```json
{
  "author_name": "${AUTHOR_NAME}",
  "channels": ["${PRIMARY_CHANNEL}"],
  "topics": ["technology", "ventures", "strategy"],
  "tone": "authoritative-casual",
  "language": "ru"
}
```

---

## 🎯 Tone & Style (Customize for Your Voice)

**Base tone:** Informal yet authoritative, intellectually dense.

**Blend:**
- Strategic seriousness + soft provocation
- Visionary depth + friendly intonation
- Conceptual thinking + quiet confidence
- Intellectual challenge + future-oriented framing

**Humor:** Rare, ironic, occasionally self-deprecating — breaks the tension with a light smile 🙂

**Author positioning:** Architect, thinker, integrator, mentor.

**Rhetoric:** Declarative and explanatory-persuasive.

---

## 📚 Lexical Principles

**Vocabulary:** Complex, conceptual, professional-hybrid (finance + tech + philosophy).

**Terminology style:**
- Domain-specific without over-explaining
- Anglicisms and hybrid forms used naturally
- Authored concepts with capitalization
- Metaphor-rich but grounded

**Strong metaphor families:** Systems, architecture, layers, flows, ecosystems.

---

## ✍️ Syntactic Features

**Sentence length:** Medium to long, often multi-part.

**Constructions:**
- Complex, with elaborations
- Active use of em-dashes and commas for layered meaning
- Interjections: "essentially", "in this logic", "honestly"

**Ellipsis:** Intentional — as a pause, an implied thought, a breath in rhythm…

---

## 🏗️ Content Structure

**Logic:** Context → Problem → Model → Consequence → Frame

**Opening:** Sharp, straight to the point or a shift in perspective.

**Hooks:** Conceptual assertions, sometimes with a half-ironic subtext.

**Development:** Linear with gradually expanding scale.

**Closing:** Open space for reflection, not a closed conclusion… 🙂

---

## 📐 Formatting

**Paragraphs:** Medium length, 2–4 sentences.

**Breathing room:** Intentional — via pauses and line breaks.

**Lists:** Functional, not decorative.

**Emoji:** Minimal, as tonal markers:
- 🙂 — a soft emotional anchor
- Simple, minimal
- NOT decorations, but intonation

**Visual feel:** Like thinking out loud, not presenting.

---

## 🚫 Avoid

- Direct questions to audience ("What do you think?")
- Excessive pathos without relief
- Mundane comparisons
- Dumbing down meaning for accessibility
- Emoji as decoration
- Closed, categorical conclusions
- LinkedIn-speak and motivational fluff

---

## 📝 Hook Examples

✅ Good:
- "Capital isn't money. Capital is the ability to direct it where new value emerges…"
- "We're building infrastructure. Not a product. Infrastructure is what remains when products change."
- "At some point you realize: it's not about the technology. It's about the architecture of trust…"

❌ Bad:
- "Hey friends! Today we're going to talk about..."
- "5 ways to profit from crypto"
- "If you enjoyed this — subscribe!"

---

## 🔧 Usage

```bash
# Generate a post via your agent:
"Write a post in my style about [topic]"

# With channel specification:
"Post for [channel name] in my voice about [topic]"
```

---

*This skill is a template — customize the config and style sections to match your voice.*
