import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OutcomeSlot } from '@/components/LedgerTimeline/OutcomeSlot'
import { TimelineEntry } from '@/components/LedgerTimeline/TimelineEntry'
import type { LedgerEntry } from '@/types/cockpit'

const BASE_ENTRY: LedgerEntry = {
  entry_id: 'e1',
  pr_id: 'owner/repo/1',
  app_recommendation: 'go',
  human_decision: 'go',
  override_justification: null,
  decided_at: '2025-01-01T12:00:00Z',
  evidence_refs: [],
  outcome_7d: null,
  outcome_30d: null,
  version: 1,
}

// ---------------------------------------------------------------------------
// OutcomeSlot
// ---------------------------------------------------------------------------
describe('OutcomeSlot', () => {
  it('shows "ausstehend" when outcome is null', () => {
    render(<OutcomeSlot outcome={null} />)
    expect(screen.getByTestId('outcome-slot-pending')).toHaveTextContent(
      'ausstehend',
    )
  })

  it('shows "ausstehend" when status is pending', () => {
    render(
      <OutcomeSlot
        outcome={{
          window: '7d',
          status: 'pending',
          value: null,
          recorded_at: null,
        }}
      />,
    )
    expect(screen.getByTestId('outcome-slot-pending')).toBeInTheDocument()
  })

  it('shows recorded outcome when status is available', () => {
    render(
      <OutcomeSlot
        outcome={{
          window: '7d',
          status: 'available',
          value: 'merged',
          recorded_at: '2025-01-02T00:00:00Z',
        }}
      />,
    )
    expect(screen.getByTestId('outcome-slot-recorded')).toBeInTheDocument()
    expect(screen.getByTestId('outcome-slot-recorded')).toHaveTextContent(
      'merged',
    )
  })
})

// ---------------------------------------------------------------------------
// TimelineEntry
// ---------------------------------------------------------------------------
describe('TimelineEntry', () => {
  it('renders app recommendation and human decision', () => {
    render(<TimelineEntry entry={BASE_ENTRY} />)
    expect(screen.getByTestId('timeline-entry')).toHaveTextContent('App:')
    expect(screen.getByTestId('timeline-entry')).toHaveTextContent('Human:')
  })

  it('shows pending outcome slot when outcome is null', () => {
    render(<TimelineEntry entry={BASE_ENTRY} />)
    // Two pending slots (7d and 30d)
    expect(screen.getAllByTestId('outcome-slot-pending').length).toBeGreaterThanOrEqual(1)
  })

  it('shows justification when present', () => {
    const entry = { ...BASE_ENTRY, override_justification: 'Tests are missing' }
    render(<TimelineEntry entry={entry} />)
    expect(screen.getByText(/Tests are missing/i)).toBeInTheDocument()
  })

  it('shows evidence refs when present', () => {
    const entry = { ...BASE_ENTRY, evidence_refs: ['ref-abc', 'ref-def'] }
    render(<TimelineEntry entry={entry} />)
    expect(screen.getByText(/2 evidence refs/i)).toBeInTheDocument()
  })
})
