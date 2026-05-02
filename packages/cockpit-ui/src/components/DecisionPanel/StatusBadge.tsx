import type { DecisionStatus } from '@/types/cockpit'

interface StatusBadgeProps {
  status: DecisionStatus
  evidenceSufficient: boolean
}

const CONFIG: Record<DecisionStatus, { label: string; colours: string }> = {
  go: {
    label: 'Go',
    colours: 'bg-green-100 text-green-800 border-green-300',
  },
  go_with_guardrails: {
    label: 'Go with Guardrails',
    colours: 'bg-amber-100 text-amber-800 border-amber-300',
  },
  no_go: {
    label: 'No-Go',
    colours: 'bg-red-100 text-red-800 border-red-300',
  },
}

export function StatusBadge({ status, evidenceSufficient }: StatusBadgeProps) {
  const effective: DecisionStatus = evidenceSufficient ? status : 'no_go'
  const { label, colours } = CONFIG[effective]

  return (
    <div data-testid="status-badge" className="inline-flex flex-col gap-1">
      <span
        className={`inline-flex items-center rounded-full border px-4 py-1.5 text-sm font-semibold ${colours}`}
      >
        {label}
      </span>
      {!evidenceSufficient && (
        <span className="text-xs text-red-600">
          Insufficient evidence — forced No-Go
        </span>
      )}
    </div>
  )
}
