import type { LedgerEntry } from '@/types/cockpit'
import { OutcomeSlot } from './OutcomeSlot'

interface TimelineEntryProps {
  entry: LedgerEntry
}

export function TimelineEntry({ entry }: TimelineEntryProps) {
  return (
    <div
      data-testid="timeline-entry"
      className="relative pl-6 pb-6 border-l-2 border-gray-200 last:border-transparent"
    >
      <span className="absolute -left-1.5 top-0 h-3 w-3 rounded-full bg-blue-400 ring-2 ring-white" />

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-1">
              {entry.decided_at
                ? new Date(entry.decided_at).toLocaleString()
                : 'Decision pending'}
            </p>
            <div className="flex gap-3 text-sm">
              <div>
                <span className="text-gray-500">App: </span>
                <span className="font-medium capitalize">
                  {entry.app_recommendation}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Human: </span>
                <span className="font-medium capitalize">
                  {entry.human_decision}
                </span>
              </div>
            </div>
            {entry.override_justification && (
              <p className="mt-1 text-xs text-gray-500 italic">
                &quot;{entry.override_justification}&quot;
              </p>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-xs text-gray-400">7d</div>
            <OutcomeSlot outcome={entry.outcome_7d} />
            <div className="text-xs text-gray-400">30d</div>
            <OutcomeSlot outcome={entry.outcome_30d} />
          </div>
        </div>
        {entry.evidence_refs && entry.evidence_refs.length > 0 && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-blue-600">
              {entry.evidence_refs.length} evidence ref
              {entry.evidence_refs.length > 1 ? 's' : ''}
            </summary>
            <ul className="mt-1 space-y-0.5">
              {entry.evidence_refs.map((ref) => (
                <li key={ref} className="font-mono text-xs text-gray-500">
                  {ref}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  )
}
