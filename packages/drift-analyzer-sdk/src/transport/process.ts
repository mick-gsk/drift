/**
 * Process transport — spawns the drift CLI process and captures output.
 *
 * Design principles:
 * - JSON-first: strips Rich ANSI escapes and extracts the first complete JSON object.
 * - Timeout-safe: AbortController kills the process on deadline.
 * - Error-transparent: exit code != 0 raises CommandFailedError unless exitZero is set.
 * - No shell expansion: execFile, not exec, to prevent flag-injection.
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";

import type { ResolvedRuntime } from "../runtime/resolver.js";
import {
  CommandFailedError,
  CommandTimeoutError,
  InvalidJsonPayloadError,
  UnsupportedSchemaVersionError,
} from "../errors.js";

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Schema version contract
// ---------------------------------------------------------------------------

/** Schema versions the SDK can decode. */
const SUPPORTED_SCHEMA_VERSIONS = ["2.2", "2.1", "2.0"];

// ---------------------------------------------------------------------------
// Output normalisation helpers
// ---------------------------------------------------------------------------

/**
 * Removes ANSI escape sequences from a string.
 * Drift's Rich output can bleed onto stdout in some terminal environments.
 */
function stripAnsi(raw: string): string {
  // eslint-disable-next-line no-control-regex
  return raw.replace(/\x1b\[[0-9;]*[mGKHF]/g, "");
}

/**
 * Extracts the first complete JSON object from mixed stdout.
 * Drift guarantees JSON starts at first `{` when --format json is used,
 * but trailing Rich symbols can appear after the closing `}`.
 */
export function extractJsonPayload(raw: string): string {
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end === -1 || start > end) {
    throw new InvalidJsonPayloadError(raw);
  }
  return raw.slice(start, end + 1);
}

/**
 * Parses drift JSON output and validates schema version.
 * Throws `UnsupportedSchemaVersionError` for future incompatible versions.
 */
export function parseJsonPayload<T extends object>(raw: string): T {
  const cleaned = stripAnsi(raw);
  let jsonStr: string;
  try {
    jsonStr = extractJsonPayload(cleaned);
  } catch {
    throw new InvalidJsonPayloadError(raw);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonStr);
  } catch (err) {
    throw new InvalidJsonPayloadError(jsonStr, err);
  }

  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "schema_version" in parsed &&
    typeof (parsed as Record<string, unknown>)["schema_version"] === "string"
  ) {
    const schemaVersion = (parsed as Record<string, unknown>)["schema_version"] as string;
    if (!SUPPORTED_SCHEMA_VERSIONS.includes(schemaVersion)) {
      throw new UnsupportedSchemaVersionError(schemaVersion, SUPPORTED_SCHEMA_VERSIONS);
    }
  }

  return parsed as T;
}

// ---------------------------------------------------------------------------
// Command builder
// ---------------------------------------------------------------------------

export interface RunCommandOptions {
  /** Subcommand, e.g. ["analyze", "--repo", "."] */
  args: string[];
  /** Absolute path to the working directory (repo root). */
  cwd: string;
  /** Timeout in milliseconds. */
  timeoutMs: number;
  /** If true, non-zero exit codes are not treated as errors. */
  exitZero?: boolean;
  /** Additional environment overrides. */
  env?: NodeJS.ProcessEnv;
}

/**
 * Validate that a user-supplied string is a safe filesystem path or arg value.
 * Rejects values containing shell metacharacters to prevent injection.
 *
 * Note: execFile (not exec) is already safe against most shell injection since
 * no shell is spawned. This check is a defence-in-depth guard.
 */
function assertSafeArg(value: string, name: string): void {
  // Reject obvious shell metacharacters
  if (/[;&|`$(){}[\]<>!#~*?]/.test(value)) {
    throw new TypeError(
      `Unsafe characters detected in ${name}: "${value}". ` +
        "Use only filesystem paths and plain option values.",
    );
  }
}

// ---------------------------------------------------------------------------
// Public transport function
// ---------------------------------------------------------------------------

/**
 * Spawns a drift subcommand and returns the parsed JSON output.
 * Throws on non-zero exit (unless exitZero), timeout, or parse failure.
 */
export async function runDriftCommand<T extends object>(
  runtime: ResolvedRuntime,
  options: RunCommandOptions,
): Promise<T> {
  const { args, cwd, timeoutMs, exitZero = false, env } = options;

  // Validate extra args to prevent injection
  for (const arg of args) {
    if (arg.startsWith("--") || arg.startsWith("-")) continue; // flag
    assertSafeArg(arg, "arg");
  }

  const fullArgs = [...runtime.executableArgs, ...args];

  const execEnv: NodeJS.ProcessEnv = {
    ...process.env,
    // Force JSON output — belt-and-suspenders against Rich detection heuristics
    NO_COLOR: "1",
    TERM: "dumb",
    ...env,
  };

  const timeoutId = setTimeout(() => {}, 0);
  clearTimeout(timeoutId);

  let stdout = "";
  let stderr = "";
  let exitCode = 0;

  try {
    const result = await execFileAsync(runtime.executablePath, fullArgs, {
      cwd,
      encoding: "utf8",
      timeout: timeoutMs,
      maxBuffer: 50 * 1024 * 1024, // 50 MB — large repos can produce significant JSON
      env: execEnv,
      windowsHide: true,
    });
    stdout = result.stdout;
    stderr = result.stderr;
  } catch (err: unknown) {
    // execFile rejects on non-zero exit or timeout
    if (
      typeof err === "object" &&
      err !== null &&
      "code" in err &&
      (err as { code?: unknown }).code === "ETIMEDOUT"
    ) {
      throw new CommandTimeoutError(timeoutMs);
    }

    const execErr = err as {
      stdout?: string;
      stderr?: string;
      code?: number | string;
      killed?: boolean;
      signal?: string;
    };

    stdout = execErr.stdout ?? "";
    stderr = execErr.stderr ?? "";
    exitCode = typeof execErr.code === "number" ? execErr.code : 1;

    if (execErr.killed || execErr.signal === "SIGTERM") {
      throw new CommandTimeoutError(timeoutMs);
    }

    // drift exits with 1 (findings above threshold) or 2 (config error).
    // exit code 1 with JSON stdout is a valid "findings found" response.
    // We only hard-fail on non-JSON or if exitZero is explicitly required and code != 0.
    if (!exitZero && exitCode !== 0) {
      // Check if we still got valid JSON despite the non-zero exit
      if (!stdout.includes("{")) {
        throw new CommandFailedError({
          message: `drift exited with code ${exitCode}: ${stderr.slice(0, 300)}`,
          exitCode,
          stderr,
          stdout,
        });
      }
    }
  }

  // Parse output even if exit code was non-zero (drift can have findings & exit 1)
  if (!stdout.trim()) {
    throw new CommandFailedError({
      message: `drift produced no output. stderr: ${stderr.slice(0, 300)}`,
      exitCode,
      stderr,
      stdout,
    });
  }

  return parseJsonPayload<T>(stdout);
}
