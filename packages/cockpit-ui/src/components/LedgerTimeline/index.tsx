'use client'

import { useEffect, useState } from 'react'
import { fetchLedger } from '@/api/client'
import type { LedgerEntry } from '@/types/cockpit'
import { TimelineEntry } from './TimelineEntry'
import { ErrorBanner } from '@/components/ErrorBanner'

interface LedgerTimelineProps {
  prId: string
}

export function LedgerTimeline({ prId }: LedgerTimelineProps) {
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchLedger(prId)
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
  }, [prId])

  if (error) return <ErrorBanner message={error} />

  return (
    <section aria-label="Decision Ledger">
      <h2 className="text-lg font-bold text-gray-900 mb-4">Decision Ledger</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-gray-500">
          No decisions recorded yet for this PR.
        </p>
      ) : (
        <div>
          {entries.map((entry) => (
            <TimelineEntry key={entry.entry_id} entry={entry} />
          ))}
        </div>
      )}
    </section>
  )
}
