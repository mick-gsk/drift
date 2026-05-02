import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DecisionSelector } from '@/components/DecisionForm/DecisionSelector'
import { JustificationField } from '@/components/DecisionForm/JustificationField'

// ---------------------------------------------------------------------------
// DecisionSelector
// ---------------------------------------------------------------------------
describe('DecisionSelector', () => {
  it('renders all three options', () => {
    render(
      <DecisionSelector
        value="go"
        recommendation="go"
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('decision-option-go')).toBeInTheDocument()
    expect(
      screen.getByTestId('decision-option-go_with_guardrails'),
    ).toBeInTheDocument()
    expect(screen.getByTestId('decision-option-no_go')).toBeInTheDocument()
  })

  it('shows recommendation star on recommended option', () => {
    render(
      <DecisionSelector
        value="go"
        recommendation="no_go"
        onChange={vi.fn()}
      />,
    )
    const noGoLabel = screen.getByTestId('decision-option-no_go')
    expect(noGoLabel).toHaveTextContent('★')
  })

  it('calls onChange when option clicked', () => {
    const onChange = vi.fn()
    render(
      <DecisionSelector
        value="go"
        recommendation="go"
        onChange={onChange}
      />,
    )
    const radio = screen.getByTestId('decision-option-no_go').querySelector('input')
    fireEvent.click(radio!)
    expect(onChange).toHaveBeenCalledWith('no_go')
  })
})

// ---------------------------------------------------------------------------
// JustificationField
// ---------------------------------------------------------------------------
describe('JustificationField', () => {
  it('renders with required indicator when required=true', () => {
    render(
      <JustificationField value="" required={true} onChange={vi.fn()} />,
    )
    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('does not render required indicator when required=false', () => {
    render(
      <JustificationField value="" required={false} onChange={vi.fn()} />,
    )
    expect(screen.queryByText('*')).not.toBeInTheDocument()
  })

  it('renders the textarea', () => {
    render(
      <JustificationField value="hello" required={false} onChange={vi.fn()} />,
    )
    expect(screen.getByTestId('justification-field')).toHaveValue('hello')
  })
})
