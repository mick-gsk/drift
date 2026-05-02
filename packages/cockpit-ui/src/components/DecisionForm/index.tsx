'use client'

import { useState } from 'react'
import { postDecision } from '@/api/client'
import type { DecisionStatus, DecisionPanel } from '@/types/cockpit'
import { DecisionSelector } from './DecisionSelector'
import { JustificationField } from './JustificationField'
import { ErrorBanner } from '@/components/ErrorBanner'

interface DecisionFormProps {
  prId: string
  panel: DecisionPanel
  onSuccess: () => void
}

export function DecisionForm({ prId, panel, onSuccess }: DecisionFormProps) {
  const [decision, setDecision] = useState<DecisionStatus>(panel.status)
  const [justification, setJustification] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [conflict, setConflict] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const differsFromRecommendation = decision !== panel.status
  const justificationRequired = differsFromRecommendation

  const canSubmit =
    !submitting && (!justificationRequired || justification.trim().length > 0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setConflict(false)
    setError(null)

    try {
      await postDecision(prId, {
        human_decision: decision,
        override_justification: justification || null,
        version: panel.version,
      })
      onSuccess()
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'status' in err) {
        const apiErr = err as { status: number }
        if (apiErr.status === 409) {
          setConflict(true)
        } else {
          setError('Failed to submit decision. Please try again.')
        }
      } else {
        setError('An unexpected error occurred.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form data-testid="decision-form" onSubmit={handleSubmit} className="space-y-4">
      {conflict && (
        <ErrorBanner
          type="conflict"
          message="Another decision was submitted concurrently. Please review the current state."
        />
      )}
      {error && <ErrorBanner message={error} />}

      <DecisionSelector
        value={decision}
        recommendation={panel.status}
        onChange={setDecision}
      />

      {differsFromRecommendation && (
        <JustificationField
          value={justification}
          required={justificationRequired}
          onChange={(e) => setJustification(e.target.value)}
        />
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? 'Submitting…' : 'Submit Decision'}
      </button>
    </form>
  )
}
