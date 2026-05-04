'use client'

import { useState } from 'react'
import type { MinimalSafePlan } from '@/types/cockpit'
import { DeltaBadge } from './DeltaBadge'
import { GuardrailChecklist } from './GuardrailChecklist'

interface MinimalSafePlanCardProps {
  plan: MinimalSafePlan
  prId: string
}

export function MinimalSafePlanCard({ plan, prId }: MinimalSafePlanCardProps) {
  const [guardrails, setGuardrails] = useState(plan.guardrails)
  const [expanded, setExpanded] = useState(false)

  const handleGuardrailChange = (conditionId: string, fulfilled: boolean) => {
    setGuardrails((prev) =>
      prev.map((g) =>
        g.condition_id === conditionId ? { ...g, fulfilled } : g,
      ),
    )
  }

  return (
    <div
      data-testid="safe-plan-card"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between text-left"
        aria-expanded={expanded ? 'true' : 'false'}
      >
        <span className="font-medium text-gray-900">{plan.title}</span>
        <div className="flex items-center gap-2">
          <DeltaBadge label="risk" value={plan.risk_delta} />
          <DeltaBadge label="score" value={plan.score_delta} />
          <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <GuardrailChecklist
            prId={prId}
            planId={plan.plan_id}
            guardrails={guardrails}
            onChange={handleGuardrailChange}
          />
        </div>
      )}
    </div>
  )
}
