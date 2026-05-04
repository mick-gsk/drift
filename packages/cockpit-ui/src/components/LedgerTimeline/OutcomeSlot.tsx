import type { OutcomeRecord } from '@/types/cockpit'

interface OutcomeSlotProps {
  outcome: OutcomeRecord | null
}

export function OutcomeSlot({ outcome }: OutcomeSlotProps) {
  if (!outcome || outcome.status === 'pending') {
    return (
      <span
        data-testid="outcome-slot-pending"
        className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-500"
      >
        ausstehend
      </span>
    )
  }

  return (
    <div data-testid="outcome-slot-recorded" className="text-sm text-gray-700">
      <span className="font-semibold capitalize">{outcome.value ?? outcome.status}</span>
      {outcome.recorded_at && (
        <span className="ml-2 text-xs text-gray-400">
          {new Date(outcome.recorded_at).toLocaleDateString()}
        </span>
      )}
    </div>
  )
}
