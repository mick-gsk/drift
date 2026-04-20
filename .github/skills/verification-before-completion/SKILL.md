---
name: verification-before-completion
description: "Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always."
argument-hint: "Describe what needs to be verified before claiming completion."
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## CRITICAL: Green Tests ≠ Done

**Tests passing is a floor, not a ceiling.** Passing all tests only proves the code doesn't visibly break existing expectations — it does NOT prove the work meets the user's actual request.

```
VERBOTEN:
  "All tests pass → task complete"
  "CI is green → it works as requested"
  "No failures → requirements fulfilled"

PFLICHT stattdessen:
  1. Re-read the original user request / issue / spec
  2. Compare actual output/behavior against each stated requirement
  3. Only then: conclude whether the requirement is met
```

This rule applies even when 100% of tests pass. Even when CI is fully green. Even when the agent "feels confident".

**Green tests prove regression safety. They do not prove intent fulfillment.**

A task is done when the user's stated requirement is demonstrably satisfied — not when the test suite is happy.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| **Requirements met** | **Re-read requirement → line-by-line checklist → each item verified** | **Tests passing — even 100% green CI** |
| **Task complete** | **Original user request re-read, every stated goal demonstrably met** | **No test failures, no errors, "looks correct"** |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- **ANY wording implying success without having run verification**
- **"All tests pass" as the sole justification for task completion**
- **Closing a task, issue, or PR based only on green CI — without re-reading the requirement**

## Key Patterns

**Tests:**
```
✅ [Run test command] → [See: 34/34 pass] → "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Build:**
```
✅ [Run build] → [See: exit 0] → "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report without independent verification
```

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
