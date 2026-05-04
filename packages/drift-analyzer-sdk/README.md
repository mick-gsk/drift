# @drift-analyzer/sdk

Node.js/TypeScript SDK for [drift-analyzer](https://github.com/mick-gsk/drift).
Calls the `drift` CLI as a child process and returns typed JSON.

## Install

```bash
# 1. drift CLI (backend)
pip install drift-analyzer

# 2. SDK
npm install @drift-analyzer/sdk
```

## Use

```typescript
import { analyze } from "@drift-analyzer/sdk";

const result = await analyze(".");
console.log(result.drift_score, result.severity);
```

That's it. `result` is fully typed — see [DriftOutput](#types) for all fields.

## All commands

| Function | CLI equivalent | Returns |
|---|---|---|
| `analyze(repo, opts?)` | `drift analyze` | `DriftOutput` |
| `check(repo, opts?)` | `drift check` | `DriftOutput` (throws on threshold breach) |
| `brief(task, repo, opts?)` | `drift brief` | `BriefOutput` |
| `fixPlan(repo, opts?)` | `drift fix-plan` | `FixPlanOutput` |
| `queryHealth()` | `drift --version` | `HealthResult` |

<details>
<summary><strong>Options reference</strong></summary>

```typescript
// analyze / check
{ since?: number; compact?: boolean; target?: string;
  baseline?: string; config?: string; timeoutMs?: number }

// check only
{ exitZero?: boolean }  // don't throw on threshold breach

// brief
{ scope?: string; maxGuardrails?: number; selectSignals?: string[];
  includeNonOperational?: boolean; config?: string; timeoutMs?: number }

// fixPlan
{ findingId?: string; signal?: string; maxTasks?: number;
  targetPath?: string; excludePaths?: string[]; includeDeferred?: boolean;
  automationFitMin?: "low" | "medium" | "high";
  includeNonOperational?: boolean; config?: string; timeoutMs?: number }
```

</details>

## Types

All types are exported from the package root.

| Type | Description |
|---|---|
| `DriftOutput` | Full output from `analyze` and `check` |
| `BriefOutput` | Output from `brief` |
| `FixPlanOutput` | Output from `fix-plan` |
| `HealthResult` | `{ ok, version, runtimePath, runtimeSource, error? }` |
| `Severity` | `"low" \| "medium" \| "high" \| "critical"` |

## Errors

All errors extend `DriftSdkError`.

| Class | When |
|---|---|
| `RuntimeNotFoundError` | `drift` not on PATH and no bundle |
| `CommandFailedError` | non-zero exit + no JSON output |
| `CommandTimeoutError` | exceeded `timeoutMs` |
| `InvalidJsonPayloadError` | CLI produced no parseable JSON |
| `UnsupportedSchemaVersionError` | future CLI version, schema changed |

```typescript
import { DriftSdkError, RuntimeNotFoundError } from "@drift-analyzer/sdk";

try {
  const result = await analyze(".");
} catch (err) {
  if (err instanceof RuntimeNotFoundError) {
    console.error("Install drift: pip install drift-analyzer");
  } else if (err instanceof DriftSdkError) {
    console.error(err.message);
  }
}
```

## Runtime resolution

The SDK finds `drift` in this order:
1. `DRIFT_BIN` env var
2. `drift` on PATH
3. `python -m drift`
4. Managed bundle (~/.cache/drift-analyzer-sdk/)

## License

MIT — see [LICENSE](../../LICENSE)
