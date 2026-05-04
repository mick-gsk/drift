import type { DecisionPanel } from '@/types/cockpit'
import { StatusBadge } from './StatusBadge'
import { ConfidenceBar } from './ConfidenceBar'
import { RiskDriverList } from './RiskDriverList'
import { LoadingIndicator } from '@/components/LoadingIndicator'

interface DecisionPanelProps {
  panel: DecisionPanel
}

export function DecisionPanelView({ panel }: DecisionPanelProps) {
  const isScanning = panel.scan_status === 'running'

  return (
    <section aria-label="Decision Status">
      <h2 className="text-lg font-bold text-gray-900 mb-4">Decision Status</h2>

      {isScanning && (
        <div className="mb-4">
          <LoadingIndicator progress={panel.scan_progress} />
        </div>
      )}

      <div className="space-y-4">
        <StatusBadge
          status={panel.status}
          evidenceSufficient={panel.evidence_sufficient}
        />

        <ConfidenceBar confidence={panel.confidence} />

        {panel.top_risk_drivers.length > 0 && (
          <RiskDriverList drivers={panel.top_risk_drivers} />
        )}
      </div>
    </section>
  )
}
