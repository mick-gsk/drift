import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// Shared mock API fixtures — intercepted via page.route()
// ---------------------------------------------------------------------------
const PR_DECISION = {
  pr_id: 'mick-gsk/drift/123',
  status: 'go',
  confidence: 0.85,
  evidence_sufficient: true,
  top_risk_drivers: [
    {
      driver_id: 'd1',
      title: 'High churn in auth module',
      impact: 0.7,
      severity: 'high',
    },
  ],
  version: 1,
  scan_status: 'complete',
  scan_progress: 100,
}

const PR_DECISION_NO_EVIDENCE = {
  ...PR_DECISION,
  pr_id: 'mick-gsk/drift/456',
  status: 'no_go',
  evidence_sufficient: false,
  top_risk_drivers: [],
}

const SAFE_PLANS = [
  {
    plan_id: 'p1',
    pr_id: 'mick-gsk/drift/123',
    title: 'Refactor auth module first',
    risk_delta: -0.2,
    score_delta: -0.1,
    guardrails: [
      { condition_id: 'g1', description: 'Add integration tests', fulfilled: false },
    ],
  },
]

const CLUSTERS = [
  {
    cluster_id: 'c1',
    label: 'Auth Module',
    risk_share: 0.65,
    dominant: true,
    files: [{ path: 'src/auth.py', contribution: 1.0 }],
  },
]

const LEDGER: object[] = [
  {
    entry_id: 'e1',
    pr_id: 'mick-gsk/drift/123',
    app_recommendation: 'go',
    human_decision: null,
    override_justification: null,
    decided_at: null,
    evidence_refs: [],
    outcome_7d: null,
    outcome_30d: null,
    version: 1,
  },
]

async function mockApiRoutes(page: Parameters<typeof test>[1] extends (args: { page: infer P }) => unknown ? P : never) {
  // Intercept all cockpit API calls regardless of base URL
  await page.route('**/api/cockpit/prs/**/decision', async (r) => {
    const url = r.request().url()
    const isPost = r.request().method() === 'POST'
    if (isPost) return r.fulfill({ json: PR_DECISION })
    if (url.includes('456')) return r.fulfill({ json: PR_DECISION_NO_EVIDENCE })
    return r.fulfill({ json: PR_DECISION })
  })
  await page.route('**/api/cockpit/prs/**/scan-status', (r) =>
    r.fulfill({ json: { status: 'complete', progress: 100 } }),
  )
  await page.route('**/api/cockpit/prs/**/safe-plan/**', (r) =>
    r.fulfill({ status: 200, body: '' }),
  )
  await page.route('**/api/cockpit/prs/**/safe-plan', (r) =>
    r.fulfill({ json: SAFE_PLANS }),
  )
  await page.route('**/api/cockpit/prs/**/clusters', (r) =>
    r.fulfill({ json: CLUSTERS }),
  )
  await page.route('**/api/cockpit/prs/**/ledger', (r) =>
    r.fulfill({ json: LEDGER }),
  )
}

// ---------------------------------------------------------------------------
// US1: Decision Panel
// ---------------------------------------------------------------------------
test.describe('US1: Decision Panel', () => {
  test('shows status badge, confidence and risk drivers', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123')
    await expect(page.getByRole('heading', { name: /Decision Status/i })).toBeVisible()
    await expect(page.getByTestId('status-badge')).toBeVisible()
    await expect(page.getByTestId('confidence-bar')).toBeVisible()
    await expect(page.getByTestId('risk-driver-item').first()).toBeVisible()
  })

  test('shows no-go when evidence is insufficient', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/456')
    await expect(page.getByTestId('status-badge')).toContainText(/no.go/i)
    await expect(page.getByText(/insufficient evidence/i)).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// US2: Minimal Safe Plans
// ---------------------------------------------------------------------------
test.describe('US2: Minimal Safe Plans', () => {
  test('shows plan card with deltas and guardrail checklist', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123?tab=plan')
    await expect(page.getByTestId('safe-plan-card').first()).toBeVisible()
    await expect(page.getByTestId('delta-badge').first()).toBeVisible()
    // expand the card to see guardrails
    await page.getByTestId('safe-plan-card').first().getByRole('button').click()
    await expect(page.getByTestId('guardrail-item').first()).toBeVisible()
  })

  test('checking a guardrail toggles without reload', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123?tab=plan')
    await page.getByTestId('safe-plan-card').first().getByRole('button').click()
    const checkbox = page.getByTestId('guardrail-item').first().getByRole('checkbox')
    await checkbox.check()
    await expect(checkbox).toBeChecked()
  })
})

// ---------------------------------------------------------------------------
// US3: Accountability Graph
// ---------------------------------------------------------------------------
test.describe('US3: Accountability Graph', () => {
  test('shows cluster nodes with risk shares', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123?tab=graph')
    await expect(page.getByTestId('cluster-node').first()).toBeVisible()
    await expect(page.getByTestId('cluster-node').first()).toContainText(/%/)
  })

  test('clicking cluster expands file list', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123?tab=graph')
    await page.getByTestId('cluster-node').first().click()
    await expect(page.getByTestId('cluster-file-item').first()).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// US4: Decision Form
// ---------------------------------------------------------------------------
test.describe('US4: Decision Form', () => {
  test('requires justification when overriding app recommendation', async ({
    page,
  }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123')
    // Click No-Go (differs from app recommendation "go")
    await page.getByTestId('decision-option-no_go').click()
    // Submit without justification — button should be disabled
    const btn = page.getByRole('button', { name: /Submit Decision/i })
    await expect(btn).toBeDisabled()
    // Justification field should be visible
    await expect(page.getByTestId('justification-field')).toBeVisible()
  })

  test('submits decision successfully', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123')
    // Submit with app recommendation (no justification needed)
    const btn = page.getByRole('button', { name: /Submit Decision/i })
    await btn.click()
    // Form should not show error
    await expect(page.getByTestId('decision-form')).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// US5: Ledger
// ---------------------------------------------------------------------------
test.describe('US5: Decision Ledger', () => {
  test('shows timeline with pending outcome slot', async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto('/cockpit/mick-gsk/drift/123?tab=ledger')
    await expect(page.getByTestId('timeline-entry')).toBeVisible()
    await expect(page.getByTestId('outcome-slot-pending').first()).toContainText(/ausstehend/i)
  })
})

// ---------------------------------------------------------------------------
// FR-014: Viewport ≥ 1024px (T050)
// ---------------------------------------------------------------------------
test.describe('FR-014: Minimum viewport', () => {
  test('cockpit renders correctly at 1024px viewport width', async ({ page }) => {
    await mockApiRoutes(page)
    await page.setViewportSize({ width: 1024, height: 768 })
    await page.goto('/cockpit/mick-gsk/drift/123')
    await expect(page.getByRole('main')).toBeVisible()
    await expect(page.getByRole('tablist')).toBeVisible()
  })
})
