/**
 * Runtime resolver — locates the drift binary on disk.
 *
 * Priority:
 *   1. Explicit path from environment variable DRIFT_BIN
 *   2. drift / drift.exe found via PATH (which/where)
 *   3. Python module invocation: python -m drift
 *   4. Managed bundle in XDG cache / AppData
 *
 * The resolver is sync-compatible for PATH checks and async for managed bundles.
 */

import { execSync, type ExecSyncOptions } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { platform } from "node:os";

import type { HealthResult } from "../types.js";
import { RuntimeNotFoundError } from "../errors.js";
import { getManagedBundlePath, isBundleProvisioned } from "./bootstrap.js";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function runSilent(cmd: string): string | null {
  try {
    const opts: ExecSyncOptions = { stdio: ["pipe", "pipe", "pipe"], encoding: "utf8" };
    return (execSync(cmd, opts) as string).trim();
  } catch {
    return null;
  }
}

function isWindows(): boolean {
  return platform() === "win32";
}

/**
 * Checks whether `drift` can be found via PATH.
 * Returns the resolved path or null.
 */
function findInPath(): string | null {
  const cmd = isWindows() ? "where drift 2>nul" : "which drift 2>/dev/null";
  const result = runSilent(cmd);
  if (result && existsSync(result.split("\n")[0].trim())) {
    return result.split("\n")[0].trim();
  }
  return null;
}

/**
 * Returns the drift version string from a given binary path,
 * or null if the binary is not functional.
 */
function queryVersion(binaryPath: string, args: string[]): string | null {
  try {
    const quotedArgs = args.map((a) => `"${a}"`).join(" ");
    const result = runSilent(`"${binaryPath}" ${quotedArgs} --version`);
    if (result) {
      // drift --version prints e.g. "drift 2.49.0" or just "2.49.0"
      const match = result.match(/(\d+\.\d+\.\d+)/);
      return match ? match[1] : result.slice(0, 20);
    }
  } catch {
    // ignore
  }
  return null;
}

// ---------------------------------------------------------------------------
// ResolvedRuntime — internal type used by the transport layer
// ---------------------------------------------------------------------------

export interface ResolvedRuntime {
  /** Absolute path to the executable. */
  executablePath: string;
  /** Extra args inserted before the drift subcommand (e.g. ["-m", "drift"]). */
  executableArgs: string[];
  runtimeSource: HealthResult["runtimeSource"];
  version: string | null;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Resolves the drift runtime to use.
 * Throws `RuntimeNotFoundError` if no runtime is available and bootstrap fails.
 */
export async function resolveRuntime(): Promise<ResolvedRuntime> {
  // 1. Explicit override
  const envBin = process.env["DRIFT_BIN"];
  if (envBin && existsSync(envBin)) {
    const version = queryVersion(envBin, []);
    return { executablePath: envBin, executableArgs: [], runtimeSource: "path", version };
  }

  // 2. drift in PATH
  const pathBin = findInPath();
  if (pathBin) {
    const version = queryVersion(pathBin, []);
    return { executablePath: pathBin, executableArgs: [], runtimeSource: "path", version };
  }

  // 3. python -m drift
  const pythonBin = isWindows() ? "python" : "python3";
  const pythonVersion = queryVersion(pythonBin, ["-m", "drift"]);
  if (pythonVersion) {
    return {
      executablePath: pythonBin,
      executableArgs: ["-m", "drift"],
      runtimeSource: "path",
      version: pythonVersion,
    };
  }

  // 4. Managed bundle
  if (await isBundleProvisioned()) {
    const bundlePath = getManagedBundlePath();
    const bundleArgs = getBundleArgs();
    const version = queryVersion(bundleArgs.executable, bundleArgs.args);
    return {
      executablePath: bundleArgs.executable,
      executableArgs: bundleArgs.args,
      runtimeSource: "bundled",
      version,
    };
  }

  throw new RuntimeNotFoundError(
    "drift runtime not found. " +
      "Install it via 'pip install drift-analyzer' or 'pipx install drift-analyzer', " +
      "or set the DRIFT_BIN environment variable to the drift binary path.",
  );
}

/**
 * Returns a health snapshot without throwing. Suitable for diagnostics.
 */
export async function queryHealth(): Promise<HealthResult> {
  try {
    const runtime = await resolveRuntime();
    return {
      ok: runtime.version !== null,
      version: runtime.version,
      runtimePath: runtime.executablePath,
      runtimeSource: runtime.runtimeSource,
    };
  } catch (err) {
    return {
      ok: false,
      version: null,
      runtimePath: "",
      runtimeSource: "path",
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// Bundle helpers (platform-specific bootstrap integration)
// ---------------------------------------------------------------------------

interface BundleSpec {
  executable: string;
  args: string[];
}

function getBundleArgs(): BundleSpec {
  const bundlePath = getManagedBundlePath();
  // The managed bundle contains a Python env; we invoke via python -m drift
  const pythonExe = isWindows()
    ? join(bundlePath, "Scripts", "python.exe")
    : join(bundlePath, "bin", "python");
  return { executable: pythonExe, args: ["-m", "drift"] };
}
