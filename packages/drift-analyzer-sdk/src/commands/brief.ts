/**
 * brief command adapter.
 * Wraps: `drift brief --task <task> --repo <path> --format json [options]`
 */

import type { BriefOutput, BriefOptions } from "../types.js";
import { resolveRuntime } from "../runtime/resolver.js";
import { runDriftCommand } from "../transport/process.js";

export type { BriefOptions };

/**
 * Runs `drift brief` to generate a structural task brief for agent delegation.
 *
 * @param task   Natural-language task description for the brief.
 * @param repo   Absolute or relative path to the repository root.
 * @param options  Optional brief configuration.
 * @returns Parsed `BriefOutput`.
 */
export async function brief(
  task: string,
  repo: string,
  options: BriefOptions = {},
): Promise<BriefOutput> {
  const runtime = await resolveRuntime();

  const args: string[] = [
    "brief",
    "--task",
    task,
    "--repo",
    repo,
    "--format",
    "json",
    "--progress",
    "none",
  ];

  if (options.scope) {
    args.push("--scope", options.scope);
  }
  if (options.maxGuardrails !== undefined) {
    args.push("--max-guardrails", String(options.maxGuardrails));
  }
  if (options.selectSignals) {
    args.push("--select", options.selectSignals.join(","));
  }
  if (options.includeNonOperational) {
    args.push("--include-non-operational");
  }
  if (options.config) {
    args.push("--config", options.config);
  }

  return runDriftCommand<BriefOutput>(runtime, {
    args,
    cwd: repo,
    timeoutMs: options.timeoutMs ?? 60_000,
    exitZero: true,
  });
}
