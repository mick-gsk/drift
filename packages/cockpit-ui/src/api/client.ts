// Typed REST client for the Drift Cockpit Backend API
// Source: specs/007-cockpit-frontend/contracts/frontend-api-contract.md

import type {
  DecisionPanel,
  MinimalSafePlan,
  AccountabilityCluster,
  LedgerEntry,
  ScanStatusResponse,
  DecisionWriteRequest,
  PrRef,
} from '@/types/cockpit'

const API_BASE = process.env.COCKPIT_API_URL || 'http://localhost:8001'
const PREFIX = `${API_BASE}/api/cockpit`

// ---------------------------------------------------------------------------
// parsePrUrl — extracts PrRef from a GitHub PR URL (FR-016)
// ---------------------------------------------------------------------------
const PR_URL_REGEX =
  /^https?:\/\/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)\/?$/

export function parsePrUrl(url: string): PrRef | null {
  const m = PR_URL_REGEX.exec(url.trim())
  if (!m) return null
  return {
    owner: m[1],
    repo: m[2],
    pr_number: parseInt(m[3], 10),
    raw_url: url.trim(),
  }
}

export function prId(ref: PrRef): string {
  return `${ref.owner}/${ref.repo}/${ref.pr_number}`
}

// ---------------------------------------------------------------------------
// Internal fetch helper with typed error handling
// ---------------------------------------------------------------------------
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PREFIX}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`API error ${status}: ${body}`)
    this.name = 'ApiError'
  }
}

// ---------------------------------------------------------------------------
// Endpoint functions
// ---------------------------------------------------------------------------

export async function fetchDecisionPanel(id: string): Promise<DecisionPanel> {
  return apiFetch<DecisionPanel>(`/prs/${encodeURIComponent(id)}/decision`)
}

export async function postDecision(
  id: string,
  body: DecisionWriteRequest,
): Promise<DecisionPanel> {
  return apiFetch<DecisionPanel>(`/prs/${encodeURIComponent(id)}/decision`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function fetchScanStatus(id: string): Promise<ScanStatusResponse> {
  return apiFetch<ScanStatusResponse>(`/prs/${encodeURIComponent(id)}/scan-status`)
}

export async function fetchSafePlans(id: string): Promise<MinimalSafePlan[]> {
  return apiFetch<MinimalSafePlan[]>(`/prs/${encodeURIComponent(id)}/safe-plan`)
}

export async function patchGuardrail(
  prId: string,
  planId: string,
  conditionId: string,
  fulfilled: boolean,
): Promise<void> {
  await apiFetch<unknown>(
    `/prs/${encodeURIComponent(prId)}/safe-plan/${encodeURIComponent(planId)}/guardrails/${encodeURIComponent(conditionId)}`,
    { method: 'PATCH', body: JSON.stringify({ fulfilled }) },
  )
}

export async function fetchClusters(
  id: string,
): Promise<AccountabilityCluster[]> {
  return apiFetch<AccountabilityCluster[]>(
    `/prs/${encodeURIComponent(id)}/clusters`,
  )
}

export async function fetchLedger(id: string): Promise<LedgerEntry[]> {
  return apiFetch<LedgerEntry[]>(`/prs/${encodeURIComponent(id)}/ledger`)
}
