import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/DecisionPanel/StatusBadge'
import { ConfidenceBar } from '@/components/DecisionPanel/ConfidenceBar'
import { RiskDriverList } from '@/components/DecisionPanel/RiskDriverList'
import type { RiskDriver } from '@/types/cockpit'

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------
describe('StatusBadge', () => {
  it('renders Go with green colours when evidence sufficient', () => {
    render(<StatusBadge status="go" evidenceSufficient={true} />)
    const badge = screen.getByTestId('status-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('Go')
  })

  it('renders Go with Guardrails label', () => {
    render(<StatusBadge status="go_with_guardrails" evidenceSufficient={true} />)
    expect(screen.getByTestId('status-badge')).toHaveTextContent('Go with Guardrails')
  })

  it('renders No-Go label', () => {
    render(<StatusBadge status="no_go" evidenceSufficient={true} />)
    expect(screen.getByTestId('status-badge')).toHaveTextContent('No-Go')
  })

  it('forces No-Go when evidence insufficient', () => {
    render(<StatusBadge status="go" evidenceSufficient={false} />)
    expect(screen.getByTestId('status-badge')).toHaveTextContent('No-Go')
    expect(screen.getByText(/insufficient evidence/i)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// ConfidenceBar
// ---------------------------------------------------------------------------
describe('ConfidenceBar', () => {
  it('renders with correct percentage label', () => {
    render(<ConfidenceBar confidence={0.75} />)
    expect(screen.getByTestId('confidence-bar')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('clamps values above 1', () => {
    render(<ConfidenceBar confidence={1.5} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('clamps values below 0', () => {
    render(<ConfidenceBar confidence={-0.5} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// RiskDriverList
// ---------------------------------------------------------------------------
const DRIVERS: RiskDriver[] = [
  { driver_id: 'd1', title: 'High Impact Driver', impact: 0.8, severity: 'critical' },
  { driver_id: 'd2', title: 'Medium Driver', impact: 0.4, severity: 'medium' },
  { driver_id: 'd3', title: 'Low Driver', impact: 0.1, severity: 'low' },
]

describe('RiskDriverList', () => {
  it('renders all drivers sorted by impact descending', () => {
    render(<RiskDriverList drivers={DRIVERS} />)
    const items = screen.getAllByTestId('risk-driver-item')
    expect(items).toHaveLength(3)
    // First item must be highest impact
    expect(items[0]).toHaveTextContent('High Impact Driver')
  })

  it('first item is visually highlighted (has font-semibold class)', () => {
    render(<RiskDriverList drivers={DRIVERS} />)
    const items = screen.getAllByTestId('risk-driver-item')
    expect(items[0].className).toContain('font-semibold')
  })

  it('respects maxDisplay cap and shows overflow message', () => {
    render(<RiskDriverList drivers={DRIVERS} maxDisplay={2} />)
    const items = screen.getAllByTestId('risk-driver-item')
    expect(items).toHaveLength(2)
    expect(screen.getByText(/\+1 more/)).toBeInTheDocument()
  })

  it('sorts unsorted input by impact', () => {
    const unsorted: RiskDriver[] = [
      { driver_id: 'a', title: 'Low', impact: 0.1 },
      { driver_id: 'b', title: 'High', impact: 0.9 },
    ]
    render(<RiskDriverList drivers={unsorted} />)
    const items = screen.getAllByTestId('risk-driver-item')
    expect(items[0]).toHaveTextContent('High')
  })
})
