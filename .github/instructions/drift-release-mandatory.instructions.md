---
applyTo: "src/drift/**"
description: "AFTER EVERY CODE CHANGE AT src/drift/ YOU MUST RUN RELEASE: python scripts/release_automation.py --full-release"
---

# MANDATORY RELEASE ENFORCEMENT

## Rule: Every src/drift/ Code Change = Automatic Release

After any successful code change to `src/drift/`:

1. Code committed to master ✓
2. Tests passed ✓
3. **IMMEDIATELY RUN THIS:**
   ```
   python scripts/release_automation.py --full-release
   ```

## That's it. One command. All automatic.

- Calculates version
- Updates files
- Creates release
- Publishes

## NO EXCEPTION. EVER.

If you forget: Code is never published. User sees nothing. Work is wasted.

## See Also

- Detailed Release Guide: `.github/skills/drift-release/SKILL.md`
- Quick Start: `/release` prompt
- Full Reference: `.github/instructions/drift-release-automation.instructions.md`
