/**
 * analyze command adapter.
 * Wraps: `drift analyze --repo <path> --format json [options]`
 */

import type { DriftOutput, AnalyzeOptions } from "../types.js";
import { resolveRuntime } from "../runtime/resolver.js";
import { runDriftCommand } from "../transport/process.js";

export type { AnalyzeOptions };

/**
 * Runs `drift analyze` on the target repository and returns parsed JSON output.
 *
 * @param repo   Absolute or relative path to the repository root to analyse.
 * @param options  Optional analysis configuration.
 * @returns Parsed `DriftOutput` with full analysis results.
 */
export async function analyze(repo: string, options: AnalyzeOptions = {}): Promise<DriftOutput> {
  const runtime = await resolveRuntime();

  const args: string[] = [
    "analyze",
    "--repo",
    repo,
    "--format",
    "json",
    "--exit-zero",
    "--progress",
    "none",
  ];

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
    exitZero: true,
  });
}
