import type { RiskDriver, Severity } from '@/types/cockpit'

interface RiskDriverListProps {
  drivers: RiskDriver[]
  maxDisplay?: number
}

const SEVERITY_COLOURS: Record<Severity, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-gray-100 text-gray-600',
}

export function RiskDriverList({
  drivers,
  maxDisplay = 10,
}: RiskDriverListProps) {
  // Sorted descending by impact (spec: stärkster Treiber visuell hervorgehoben)
  const sorted = [...drivers].sort((a, b) => b.impact - a.impact)
  const visible = sorted.slice(0, maxDisplay)
  const hidden = sorted.length - visible.length

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Top Risk Drivers
      </h3>
      <ul className="space-y-2" data-testid="risk-driver-list">
        {visible.map((d, idx) => (
          <li
            key={d.driver_id}
            data-testid="risk-driver-item"
            className={`flex items-center justify-between rounded-md px-3 py-2 border ${
              idx === 0
                ? 'bg-red-50 border-red-200 font-semibold'
                : 'bg-white border-gray-100'
            }`}
          >
            <span className="text-sm text-gray-800">{d.title}</span>
            <div className="flex items-center gap-2">
              {d.severity && (
                <span
                  className={`text-xs rounded px-1.5 py-0.5 ${SEVERITY_COLOURS[d.severity]}`}
                >
                  {d.severity}
                </span>
              )}
              <span className="text-xs font-mono text-gray-500">
                {Math.round(d.impact * 100)}%
              </span>
            </div>
          </li>
        ))}
      </ul>
      {hidden > 0 && (
        <p className="mt-2 text-xs text-gray-500">
          +{hidden} more risk driver{hidden !== 1 ? 's' : ''} (not shown)
        </p>
      )}
    </div>
  )
}
