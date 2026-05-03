/**
 * Public re-export barrel for @drift-analyzer/sdk.
 *
 * All public surface is exported from this module.
 * Internal modules (transport, runtime internals) are not exported.
 */

// Types
export type {
  Severity,
  FindingStatus,
  TrendDirection,
  FindingCompact,
  FixFirstFinding,
  AnalysisStatus,
  Trend,
  Summary,
  CompactSummary,
  ModuleScore,
  BaselineInfo,
  DriftOutput,
  BriefOutput,
  FixPlanOutput,
  SignalStatus,
  AnalyzeOptions,
  CheckOptions,
  BriefOptions,
  FixPlanOptions,
  HealthResult,
} from "./types.js";

// Errors
export {
  DriftSdkError,
  RuntimeNotFoundError,
  BootstrapFailedError,
  RuntimeChecksumError,
  CommandFailedError,
  CommandTimeoutError,
  InvalidJsonPayloadError,
  UnsupportedSchemaVersionError,
} from "./errors.js";

// Commands
export { analyze } from "./commands/analyze.js";
export { check } from "./commands/check.js";
export { brief } from "./commands/brief.js";
export { fixPlan } from "./commands/fix-plan.js";

// Runtime management
export { queryHealth, provisionBundle, isBundleProvisioned } from "./runtime/index.js";
