---
description: Predefined agents available in the Drift workspace
---

# Drift Agents

## 🚀 Release Agent

**Quick Release** — After code changes to `src/drift/`, use this agent to quickly handle the full release workflow.

### How to Use

In the chat, mention:
- "Release version"
- "Create release"
- "Publish to PyPI"

The agent will:
1. Validate code quality
2. Calculate semantic version
3. Update CHANGELOG + pyproject.toml
4. Create release commit + tag
5. Push to GitHub
6. Trigger PyPI publication

### Single Command Alternative

If you prefer command-line:

```bash
python scripts/release_automation.py --full-release
```

### When to Use

✅ After: `feat:`, `fix:`, or `BREAKING:` commits to `src/drift/`  
✅ When: Tests pass and code is committed  
❌ Don't use: For incomplete work or failing tests

---

## Skills Available

- **`/release`** — Full release workflow (recommended shortcut)
- Use `/` in chat to discover available prompts/skills

---

## Documentation

- **Release Skill:** `.github/skills/drift-release/SKILL.md`
- **Release Instructions:** `.github/instructions/drift-release-automation.instructions.md`
- **Release Prompt:** `/release`
