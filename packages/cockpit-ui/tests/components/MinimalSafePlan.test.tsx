import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DeltaBadge } from '@/components/MinimalSafePlanCard/DeltaBadge'
import { GuardrailChecklist } from '@/components/MinimalSafePlanCard/GuardrailChecklist'
import { MinimalSafePlanCard } from '@/components/MinimalSafePlanCard'
import type { MinimalSafePlan } from '@/types/cockpit'

// ---------------------------------------------------------------------------
// DeltaBadge
// ---------------------------------------------------------------------------
describe('DeltaBadge', () => {
  it('shows negative delta as green (improvement)', () => {
    const { container } = render(<DeltaBadge label="risk" value={-0.15} />)
    const badge = screen.getByTestId('delta-badge')
    expect(badge.className).toContain('green')
    expect(badge).toHaveTextContent('-0.15')
  })

  it('shows positive delta as red (degradation)', () => {
    render(<DeltaBadge label="risk" value={0.1} />)
    const badge = screen.getByTestId('delta-badge')
    expect(badge.className).toContain('red')
    expect(badge).toHaveTextContent('+0.10')
  })
})

// ---------------------------------------------------------------------------
// GuardrailChecklist
// ---------------------------------------------------------------------------
const GUARDRAILS = [
  { condition_id: 'g1', description: 'Add tests', fulfilled: false },
  { condition_id: 'g2', description: 'Review docs', fulfilled: false },
]

describe('GuardrailChecklist', () => {
  it('renders all guardrail items', () => {
    render(
      <GuardrailChecklist
        prId="owner/repo/1"
        planId="p1"
        guardrails={GUARDRAILS}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getAllByTestId('guardrail-item')).toHaveLength(2)
  })

  it('calls onChange when checkbox is toggled', () => {
    const onChange = vi.fn()
    render(
      <GuardrailChecklist
        prId="owner/repo/1"
        planId="p1"
        guardrails={GUARDRAILS}
        onChange={onChange}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    expect(onChange).toHaveBeenCalledWith('g1', true)
  })

  it('shows completion badge when all fulfilled', () => {
    const allFulfilled = GUARDRAILS.map((g) => ({ ...g, fulfilled: true }))
    render(
      <GuardrailChecklist
        prId="owner/repo/1"
        planId="p1"
        guardrails={allFulfilled}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('completion-badge')).toBeInTheDocument()
  })

  it('does not show completion badge when not all fulfilled', () => {
    render(
      <GuardrailChecklist
        prId="owner/repo/1"
        planId="p1"
        guardrails={GUARDRAILS}
        onChange={vi.fn()}
      />,
    )
    expect(screen.queryByTestId('completion-badge')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// MinimalSafePlanCard
// ---------------------------------------------------------------------------
const PLAN: MinimalSafePlan = {
  plan_id: 'p1',
  pr_id: 'owner/repo/1',
  title: 'Refactor auth module',
  risk_delta: -0.2,
  score_delta: -0.1,
  guardrails: [
    { condition_id: 'g1', description: 'Add tests', fulfilled: false },
  ],
}

describe('MinimalSafePlanCard', () => {
  it('renders collapsed by default with delta badges', () => {
    render(<MinimalSafePlanCard plan={PLAN} prId="owner/repo/1" />)
    expect(screen.getByTestId('safe-plan-card')).toBeInTheDocument()
    expect(screen.getAllByTestId('delta-badge')).toHaveLength(2)
    // Guardrail should not be visible before expand
    expect(screen.queryByTestId('guardrail-item')).not.toBeInTheDocument()
  })

  it('expands on click revealing guardrail checklist', () => {
    render(<MinimalSafePlanCard plan={PLAN} prId="owner/repo/1" />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByTestId('guardrail-item')).toBeInTheDocument()
  })

  it('shows empty state for plan with no guardrails', () => {
    const emptyPlan = { ...PLAN, guardrails: [] }
    render(<MinimalSafePlanCard plan={emptyPlan} prId="owner/repo/1" />)
    fireEvent.click(screen.getByRole('button'))
    // no guardrail items
    expect(screen.queryByTestId('guardrail-item')).not.toBeInTheDocument()
  })
})
