// Cockpit Frontend TypeScript Types
// Source: specs/007-cockpit-frontend/data-model.md

export type DecisionStatus = 'go' | 'go_with_guardrails' | 'no_go'
export type ScanStatus = 'complete' | 'running' | 'not_started'
export type OutcomeStatus = 'pending' | 'available'
export type Severity = 'critical' | 'high' | 'medium' | 'low'

// ---------------------------------------------------------------------------
// PrRef — Identifies a GitHub Pull Request parsed from its URL
// ---------------------------------------------------------------------------
export interface PrRef {
  owner: string
  repo: string
  pr_number: number
  raw_url: string
}

// ---------------------------------------------------------------------------
// RiskDriver — A single risk factor contributing to the decision status
// ---------------------------------------------------------------------------
export interface RiskDriver {
  driver_id: string
  title: string
  impact: number          // 0–1
  severity?: Severity
  cluster_id?: string
}

// ---------------------------------------------------------------------------
// DecisionPanel — Primary view state for a single PR
// ---------------------------------------------------------------------------
export interface DecisionPanel {
  pr_id: string
  status: DecisionStatus
  confidence: number      // 0–1
  evidence_sufficient: boolean
  top_risk_drivers: RiskDriver[]
  version: number
  scan_status: ScanStatus
  scan_progress: number   // 0–100; meaningful when scan_status = 'running'
}

// ---------------------------------------------------------------------------
// GuardrailCondition — Single pre-merge condition within a plan
// ---------------------------------------------------------------------------
export interface GuardrailCondition {
  condition_id: string
  description: string
  fulfilled: boolean
}

// ---------------------------------------------------------------------------
// MinimalSafePlan — One actionable plan reducing risk
// ---------------------------------------------------------------------------
export interface MinimalSafePlan {
  plan_id: string
  pr_id: string
  title: string
  risk_delta: number      // negative = improvement
  score_delta: number
  guardrails: GuardrailCondition[]
}

// ---------------------------------------------------------------------------
// ClusterFile — Member file in an AccountabilityCluster
// ---------------------------------------------------------------------------
export interface ClusterFile {
  path: string
  contribution: number    // 0–1
}

// ---------------------------------------------------------------------------
// AccountabilityCluster — Group of related PR changes with risk contribution
// ---------------------------------------------------------------------------
export interface AccountabilityCluster {
  cluster_id: string
  label: string
  risk_share: number      // 0–1
  files: ClusterFile[]
  dominant: boolean
}

// ---------------------------------------------------------------------------
// OutcomeRecord — Post-merge outcome measurement
// ---------------------------------------------------------------------------
export interface OutcomeRecord {
  window: '7d' | '30d'
  status: OutcomeStatus
  value: string | null
  recorded_at: string | null  // ISO8601
}

// ---------------------------------------------------------------------------
// LedgerEntry — Full decision audit record for a PR
// ---------------------------------------------------------------------------
export interface LedgerEntry {
  entry_id: string
  pr_id: string
  app_recommendation: DecisionStatus
  human_decision: DecisionStatus | null
  override_justification: string | null
  decided_at: string | null   // ISO8601
  evidence_refs: string[]
  outcome_7d: OutcomeRecord | null
  outcome_30d: OutcomeRecord | null
  version: number
}

// ---------------------------------------------------------------------------
// CockpitStore — React context shape
// ---------------------------------------------------------------------------
export interface CockpitStore {
  prRef: PrRef | null
  panel: DecisionPanel | null
  safePlans: MinimalSafePlan[]
  clusters: AccountabilityCluster[]
  ledger: LedgerEntry | null
  loading: boolean
  error: string | null
}

// ---------------------------------------------------------------------------
// API Request/Response types
// ---------------------------------------------------------------------------
export interface DecisionWriteRequest {
  human_decision: DecisionStatus
  override_justification: string | null
  version: number
}

export interface ScanStatusResponse {
  status: ScanStatus
  progress: number
}

export interface VersionConflictError {
  code: 'version_conflict'
  message: string
  current_version: number
}
