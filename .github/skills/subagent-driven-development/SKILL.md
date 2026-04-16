---
name: subagent-driven-development
description: "Use when executing implementation plans with independent tasks in the current session. Dispatches fresh subagent per task with two-stage review (spec compliance, then code quality)."
argument-hint: "Provide the path to the implementation plan to execute."
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

## When to Use

- You have an implementation plan (from writing-plans skill)
- Tasks are mostly independent
- You want to stay in this session

**vs. Executing Plans:** Same session, fresh context per task, faster iteration with no human-in-loop between tasks.

## The Process

1. **Read plan once** — extract all tasks with full text and context
2. **Create TodoWrite** with all tasks
3. **Per task:**
   - Dispatch implementer subagent with full task text + scene-setting context
   - Answer any questions before letting them proceed
   - Implementer implements, tests, commits, self-reviews
   - Dispatch **spec compliance reviewer** subagent
   - If spec issues found: implementer fixes → re-review
   - Dispatch **code quality reviewer** subagent
   - If quality issues found: implementer fixes → re-review
   - Mark task complete
4. After all tasks: dispatch final code reviewer for entire implementation
5. Use `superpowers:finishing-a-development-branch`

## Model Selection

- **Mechanical tasks** (isolated functions, clear specs, 1-2 files): cheap/fast model
- **Integration tasks** (multi-file, pattern matching, debugging): standard model
- **Architecture/design/review**: most capable model

## Handling Implementer Status

- **DONE:** Proceed to spec compliance review
- **DONE_WITH_CONCERNS:** Read concerns before proceeding. Address correctness/scope concerns first.
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Assess blocker — more context, more capable model, smaller task, or escalate to human

**Never** ignore an escalation or force the same model to retry without changes.

## Prompt Templates

- `./implementer-prompt.md` — Dispatch implementer subagent
- `./spec-reviewer-prompt.md` — Dispatch spec compliance reviewer subagent
- `./code-quality-reviewer-prompt.md` — Dispatch code quality reviewer subagent

## Red Flags

**Never:**
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Make subagent read plan file (provide full text instead)
- Skip scene-setting context
- Accept "close enough" on spec compliance
- **Start code quality review before spec compliance is ✅**
- Move to next task while either review has open issues

## Integration

**Required workflow skills:**
- `superpowers:writing-plans` — Creates the plan this skill executes
- `superpowers:test-driven-development` — Subagents follow TDD for each task
- `superpowers:finishing-a-development-branch` — Complete development after all tasks
