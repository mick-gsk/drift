---
name: drift-security-triage
description: "Security report triage workflow for drift. Use when evaluating incoming vulnerability reports, GitHub Security Advisories, or Dependabot alerts."
---

# Drift Security Triage Skill

## Purpose

Guide Copilot agents through consistent, policy-aligned triage of security reports for the drift repository.

## When to Use

- Evaluating a new GitHub Security Advisory (GHSA)
- Triaging a vulnerability report submitted via email or private advisory
- Assessing Dependabot security alerts
- Responding to CodeQL or detect-secrets findings

## Triage Workflow

### Step 1: Trust Model Check

Drift operates under the **same trust level as local shell access**. Before classifying severity, determine:

1. **Does the vulnerability require prior write access to the target repository?**
   → If YES: likely **out of scope** (attacker already has equal privileges).

2. **Does drift execute any analyzed code?**
   → No. drift uses `ast.parse()` and tree-sitter for parsing — no code execution.

3. **Does drift make network requests?**
   → No. drift is fully local — no exfiltration vector exists.

### Step 2: Out-of-Scope Classification

The following are explicitly NOT vulnerabilities in drift (see SECURITY.md):

| Category | Reason |
| --- | --- |
| Malicious source files causing misleading findings | Same trust boundary — attacker already has write access |
| Resource exhaustion on huge repositories | Operational concern, not a vulnerability |
| Static analysis false positives | Signal quality issue — use false-positive template |
| Secret-scanning baseline entries | Intentional test fixtures with non-reversible hashes |
| Git history tampering | History integrity is the repo owner's responsibility |

If the report matches any of these → respond with the out-of-scope template (Step 5).

### Step 3: Severity Assessment

For in-scope vulnerabilities, assess using CVSS v3.1 principles:

| Factor | drift-specific consideration |
| --- | --- |
| Attack vector | Always **Local** (drift requires file system access) |
| Privileges required | At minimum **Low** (read access to target repo) |
| User interaction | Typically **Required** (user must invoke drift) |
| Scope | **Unchanged** (drift cannot escape its process boundary) |
| Confidentiality | drift reads files user already has access to — typically **None** |
| Integrity | drift produces reports — at most **Low** (misleading output) |
| Availability | Resource exhaustion possible — **Low** to **Medium** |

### Step 4: Response Timeline

Per SECURITY.md commitments:

- **Acknowledgment:** within 72 hours
- **Resolution timeline:** within 7 days of acknowledgment
- **Coordinated disclosure:** patch before public disclosure

### Step 5: Response Templates

#### Out-of-Scope Response

```markdown
Thank you for your report. After review against our [Trust Model](SECURITY.md#trust-model),
this finding falls outside drift's security scope:

**Category:** [category from out-of-scope table]
**Reason:** [specific reason]

drift operates at the same trust level as local shell access. [Brief explanation
of why this specific scenario is not a vulnerability.]

If you believe this assessment is incorrect, please provide additional context
about an attack scenario that does not require prior repository write access.
```

#### In-Scope Acknowledgment

```markdown
Thank you for your security report. We've confirmed this is within drift's
security scope and are investigating.

**Tracking:** [internal reference / GHSA ID]
**Severity assessment:** [Low/Medium/High/Critical]
**Expected resolution timeline:** [date]

We follow coordinated disclosure and will notify you before any public advisory.
```

## Dependabot Alert Triage

For dependency vulnerabilities:

1. Check if the vulnerable dependency is in `[project.dependencies]` (runtime) or `[project.optional-dependencies.dev]` (dev-only)
2. Dev-only dependencies have **reduced severity** (not shipped to users)
3. Runtime dependencies affecting drift's actual usage patterns are **high priority**
4. Update via `pip install --upgrade <package>` → regenerate `uv.lock` → test → release
