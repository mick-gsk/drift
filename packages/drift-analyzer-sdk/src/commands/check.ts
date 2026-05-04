/**
 * check command adapter.
 * Wraps: `drift check --repo <path> --format json [options]`
 */

import type { DriftOutput, CheckOptions } from "../types.js";
import { resolveRuntime } from "../runtime/resolver.js";
import { runDriftCommand } from "../transport/process.js";

export type { CheckOptions };

/**
 * Runs `drift check` on the target repository.
 * Exits with a non-zero code when findings exceed the configured threshold.
 * The SDK translates this to `CommandFailedError` unless `exitZero` is set.
 *
 * @param repo   Absolute or relative path to the repository root.
 * @param options  Optional check configuration.
 * @returns Parsed `DriftOutput` (same schema as analyze).
 */
export async function check(repo: string, options: CheckOptions = {}): Promise<DriftOutput> {
  const runtime = await resolveRuntime();

  const args: string[] = [
    "check",
    "--repo",
    repo,
    "--format",
    "json",
    "--progress",
    "none",
  ];

  if (options.exitZero) {
    args.push("--exit-zero");
  }
  if (options.since !== undefined) {
    args.push("--since-days", String(options.since));
  }
  if (options.compact) {
    args.push("--compact");
  }
  if (options.target) {
    args.push("--target", options.target);
  }
  if (options.baseline) {
    args.push("--baseline", options.baseline);
  }
  if (options.config) {
    args.push("--config", options.config);
  }

  return runDriftCommand<DriftOutput>(runtime, {
    args,
    cwd: repo,
    timeoutMs: options.timeoutMs ?? 120_000,
    exitZero: options.exitZero ?? false,
  });
}
