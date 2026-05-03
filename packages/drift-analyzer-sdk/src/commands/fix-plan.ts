/**
 * fix-plan command adapter.
 * Wraps: `drift fix-plan --repo <path> --format json [options]`
 */

import type { FixPlanOutput, FixPlanOptions } from "../types.js";
import { resolveRuntime } from "../runtime/resolver.js";
import { runDriftCommand } from "../transport/process.js";

export type { FixPlanOptions };

/**
 * Runs `drift fix-plan` to generate a prioritised list of repair tasks.
 *
 * @param repo   Absolute or relative path to the repository root.
 * @param options  Optional fix-plan configuration.
 * @returns Parsed `FixPlanOutput`.
 */
export async function fixPlan(repo: string, options: FixPlanOptions = {}): Promise<FixPlanOutput> {
  const runtime = await resolveRuntime();

  const args: string[] = [
    "fix-plan",
    "--repo",
    repo,
    "--format",
    "json",
    "--progress",
    "none",
  ];

  if (options.findingId) {
    args.push("--finding-id", options.findingId);
  }
  if (options.signal) {
    args.push("--signal", options.signal);
  }
  if (options.maxTasks !== undefined) {
    args.push("--max-tasks", String(options.maxTasks));
  }
  if (options.targetPath) {
    args.push("--target-path", options.targetPath);
  }
  if (options.excludePaths) {
    for (const p of options.excludePaths) {
      args.push("--exclude", p);
    }
  }
  if (options.includeDeferred) {
    args.push("--include-deferred");
  }
  if (options.automationFitMin) {
    args.push("--automation-fit-min", options.automationFitMin);
  }
  if (options.includeNonOperational) {
    args.push("--include-non-operational");
  }
  if (options.config) {
    args.push("--config", options.config);
  }

  return runDriftCommand<FixPlanOutput>(runtime, {
    args,
    cwd: repo,
    timeoutMs: options.timeoutMs ?? 90_000,
    exitZero: true,
  });
}
