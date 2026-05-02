'use client'

import { Suspense } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { useDecisionPanel } from '@/hooks/useDecisionPanel'
import { useScanStatus } from '@/hooks/useScanStatus'
import { ErrorBanner } from '@/components/ErrorBanner'
import { LoadingIndicator } from '@/components/LoadingIndicator'
import { DecisionPanelView } from '@/components/DecisionPanel'
import { DecisionForm } from '@/components/DecisionForm'
import { MinimalSafePlanList } from '@/components/MinimalSafePlanList'
import { AccountabilityGraph } from '@/components/AccountabilityGraph'
import { LedgerTimeline } from '@/components/LedgerTimeline'
import type { PrRef } from '@/types/cockpit'
import { prId } from '@/api/client'

interface CockpitShellProps {
  prRef: PrRef
}

const TABS = [
  { id: 'panel', label: 'Decision Panel' },
  { id: 'plan', label: 'Safe Plan' },
  { id: 'graph', label: 'Graph' },
  { id: 'ledger', label: 'Ledger' },
]

function CockpitShellInner({ prRef }: CockpitShellProps) {
  const id = prId(prRef)
  const { panel, loading, error, refetch } = useDecisionPanel(id)
  const { status: scanStatus, progress } = useScanStatus(id)
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const tab = searchParams?.get('tab') ?? 'panel'

  const navigateTab = (tabId: string) => {
    const params = new URLSearchParams(searchParams?.toString() ?? '')
    params.set('tab', tabId)
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Drift Cockpit — {prRef.owner}/{prRef.repo} #{prRef.pr_number}
        </h1>
      </header>

      {scanStatus === 'running' && (
        <div className="mb-4">
          <LoadingIndicator progress={progress} />
        </div>
      )}

      {error === 'not_found' && (
        <ErrorBanner
          message="This PR has not been analysed yet. Run `drift cockpit build --pr <id>` to start."
          type="error"
        />
      )}
      {error && error !== 'not_found' && (
        <ErrorBanner message={error} type="error" />
      )}

      {/* Tab bar */}
      <nav
        aria-label="Cockpit sections"
        role="tablist"
        className="flex gap-1 border-b border-gray-200 mb-6"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id ? ('true' as const) : ('false' as const)}
            onClick={() => navigateTab(t.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
              tab === t.id
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="space-y-6" data-testid="cockpit-content">
        {loading && !panel && (
          <p className="text-sm text-gray-400 animate-pulse">Loading…</p>
        )}

        {tab === 'panel' && !error && (
          <>
            {panel && <DecisionPanelView panel={panel} />}
            {panel && (
              <DecisionForm prId={id} panel={panel} onSuccess={refetch} />
            )}
          </>
        )}

        {tab === 'plan' && <MinimalSafePlanList prId={id} />}
        {tab === 'graph' && <AccountabilityGraph prId={id} />}
        {tab === 'ledger' && <LedgerTimeline prId={id} />}
      </div>
    </main>
  )
}

export function CockpitShell({ prRef }: CockpitShellProps) {
  return (
    <Suspense fallback={<p className="text-sm text-gray-400 p-8">Loading…</p>}>
      <CockpitShellInner prRef={prRef} />
    </Suspense>
  )
}
