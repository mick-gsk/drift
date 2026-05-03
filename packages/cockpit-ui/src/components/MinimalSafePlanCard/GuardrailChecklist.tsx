'use client'

import { useCallback, useRef } from 'react'
import { patchGuardrail } from '@/api/client'
import type { GuardrailCondition } from '@/types/cockpit'

interface GuardrailChecklistProps {
  prId: string
  planId: string
  guardrails: GuardrailCondition[]
  onChange: (conditionId: string, fulfilled: boolean) => void
}

const DEBOUNCE_MS = 400

export function GuardrailChecklist({
  prId,
  planId,
  guardrails,
  onChange,
}: GuardrailChecklistProps) {
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const handleToggle = useCallback(
    (condition: GuardrailCondition) => {
      const next = !condition.fulfilled
      onChange(condition.condition_id, next)

      const existing = timers.current.get(condition.condition_id)
      if (existing) clearTimeout(existing)

      const timer = setTimeout(async () => {
        try {
          await patchGuardrail(prId, planId, condition.condition_id, next)
        } catch {
          // revert optimistic update on failure
          onChange(condition.condition_id, condition.fulfilled)
        }
      }, DEBOUNCE_MS)
      timers.current.set(condition.condition_id, timer)
    },
    [prId, planId, onChange],
  )

  const allFulfilled =
    guardrails.length > 0 && guardrails.every((g) => g.fulfilled)

  return (
    <div>
      {allFulfilled && (
        <div
          data-testid="completion-badge"
          className="mb-2 rounded-md bg-green-50 border border-green-200 px-3 py-1.5 text-xs text-green-700 font-medium"
        >
          All guardrails fulfilled
        </div>
      )}
      <ul className="space-y-1">
        {guardrails.map((g) => (
          <li key={g.condition_id} data-testid="guardrail-item">
            <label className="flex items-start gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={g.fulfilled}
                onChange={() => handleToggle(g)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <span className={g.fulfilled ? 'line-through text-gray-400' : ''}>
                {g.description}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}
