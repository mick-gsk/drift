/**
 * TypeScript types for the @drift-analyzer/sdk.
 *
 * Core output types derived from drift.output.schema.json (v2.2).
 * Schema version: 2.2 — additive changes are backward compatible.
 */

// ---------------------------------------------------------------------------
// Primitive enumerations
// ---------------------------------------------------------------------------

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type FindingStatus = "active" | "suppressed" | "resolved";

export type TrendDirection = "improving" | "degrading" | "stable" | "baseline";

// ---------------------------------------------------------------------------
// Finding shapes
// ---------------------------------------------------------------------------

export interface FindingCompact {
  /** Deterministic content-based fingerprint (SHA256 prefix, 16 hex chars). */
  finding_id: string;
  rank: number;
  signal: string;
  signal_abbrev?: string;
  rule_id?: string | null;
  severity: Severity;
  status?: FindingStatus;
  finding_context?: string;
  impact?: number;
  score_contribution?: number;
  title: string;
  file?: string | null;
  start_line?: number | null;
  duplicate_count?: number;
  next_step?: string | null;
}

export interface FixFirstFinding extends FindingCompact {
  priority_class?: string;
  expected_benefit?: string;
}

// ---------------------------------------------------------------------------
// Analysis sub-structures
// ---------------------------------------------------------------------------

export interface AnalysisStatus {
  status: string;
  degraded: boolean;
  is_fully_reliable: boolean;
  causes: string[];
  affected_components: string[];
  events: unknown[];
}

export interface Trend {
  previous_score: number | null;
  delta: number | null;
  direction: TrendDirection;
  recent_scores: number[];
  history_depth: number;
  transition_ratio: number | null;
}

export interface Summary {
  total_files?: number;
  total_functions?: number;
  ai_attributed_ratio?: number;
  ai_tools_detected?: string[];
  analysis_duration_seconds?: number | null;
}

export interface CompactSummary {
  findings_total?: number;
  findings_deduplicated?: number;
  duplicate_findings_removed?: number;
  suppressed_total?: number;
  critical_count?: number;
  high_count?: number;
  fix_first_count?: number;
}

export interface ModuleScore {
  path: string;
  drift_score: number;
  severity: Severity;
  signal_scores?: Record<string, number>;
  finding_count: number;
  ai_ratio?: number;
}

export interface BaselineInfo {
  applied: boolean;
  new_findings_count?: number | null;
  baseline_matched_count?: number | null;
}

// ---------------------------------------------------------------------------
// Top-level output (drift analyze --format json)
// ---------------------------------------------------------------------------

export interface DriftOutput {
  schema_version: string;
  version: string;
  signal_abbrev_map?: Record<string, string>;
  repo: string;
  analyzed_at: string;
  drift_score: number;
  drift_score_scope?: string;
  severity: Severity;
  grade?: string;
  grade_label?: string;
  analysis_status?: AnalysisStatus;
  trend?: Trend | null;
  summary?: Summary;
  findings_compact?: FindingCompact[];
  compact_summary?: CompactSummary;
  fix_first?: FixFirstFinding[];
  suppressed_count?: number;
  context_tagged_count?: number;
  baseline?: BaselineInfo | null;
  modules?: ModuleScore[];
}

// ---------------------------------------------------------------------------
// Brief output
// ---------------------------------------------------------------------------

export interface BriefOutput {
  schema_version?: string;
  repo?: string;
  brief?: string;
  /** Raw structured response from drift brief --format json */
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Fix-plan output
// ---------------------------------------------------------------------------

export interface FixPlanTask {
  id?: string;
  finding_id?: string;
  title?: string;
  severity?: Severity;
  description?: string;
  constraints?: string[];
  verification_plan?: string[];
  [key: string]: unknown;
}

export interface FixPlanOutput {
  schema_version?: string;
  repo?: string;
  tasks?: FixPlanTask[];
  /** Raw structured response from drift fix-plan --format json */
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Signal status (derived helper — not from wire, built by SDK)
// ---------------------------------------------------------------------------

export interface SignalStatus {
  abbrev: string;
  name: string;
  severity: Severity | "pass";
  findings: FindingCompact[];
}

// ---------------------------------------------------------------------------
// SDK option shapes
// ---------------------------------------------------------------------------

export interface AnalyzeOptions {
  /** Limit analysis to files changed in the last N days. */
  since?: number;
  /** Return compact JSON (smaller payload). */
  compact?: boolean;
  /** Restrict analysis to a subdirectory or file glob. */
  target?: string;
  /** Path to a baseline file or git ref for new-finding delta mode. */
  baseline?: string;
  /** Path to a drift.yaml config file. */
  config?: string;
  /** Timeout in milliseconds. Default: 120 000. */
  timeoutMs?: number;
}

export interface CheckOptions extends AnalyzeOptions {
  /** If true, always exit with 0 regardless of findings. */
  exitZero?: boolean;
}

export interface BriefOptions {
  /** Manual scope override (path or glob). */
  scope?: string;
  /** Maximum number of guardrails to generate (1–50). Default: 10. */
  maxGuardrails?: number;
  /** Comma-separated signal IDs to evaluate (e.g. ["PFS","AVS"]). */
  selectSignals?: string[];
  /** Include fixture/generated/migration/docs findings. */
  includeNonOperational?: boolean;
  /** Path to a drift.yaml config file. */
  config?: string;
  /** Timeout in milliseconds. Default: 60 000. */
  timeoutMs?: number;
}

export interface FixPlanOptions {
  /** Target a specific finding by task id or rule_id. */
  findingId?: string;
  /** Filter to a specific signal (e.g. "PFS"). */
  signal?: string;
  /** Maximum tasks to return. Default: 5. */
  maxTasks?: number;
  /** Restrict tasks to findings inside this subpath. */
  targetPath?: string;
  /** Exclude findings inside these subpaths. */
  excludePaths?: string[];
  /** Include findings marked as deferred in drift config. */
  includeDeferred?: boolean;
  /** Minimum automation fitness: "low" | "medium" | "high". */
  automationFitMin?: "low" | "medium" | "high";
  /** Include fixture/generated/migration/docs findings. */
  includeNonOperational?: boolean;
  /** Path to a drift.yaml config file. */
  config?: string;
  /** Timeout in milliseconds. Default: 90 000. */
  timeoutMs?: number;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export interface HealthResult {
  ok: boolean;
  version: string | null;
  runtimePath: string;
  runtimeSource: "path" | "bundled" | "managed";
  error?: string;
}
