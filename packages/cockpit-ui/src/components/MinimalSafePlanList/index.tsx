'use client'

import { useEffect, useState } from 'react'
import { fetchSafePlans } from '@/api/client'
import type { MinimalSafePlan } from '@/types/cockpit'
import { MinimalSafePlanCard } from '@/components/MinimalSafePlanCard'
import { ErrorBanner } from '@/components/ErrorBanner'

interface MinimalSafePlanListProps {
  prId: string
}

export function MinimalSafePlanList({ prId }: MinimalSafePlanListProps) {
  const [plans, setPlans] = useState<MinimalSafePlan[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSafePlans(prId)
      .then(setPlans)
      .catch((e: Error) => setError(e.message))
  }, [prId])

  if (error) return <ErrorBanner message={error} />

  if (plans.length === 0)
    return (
      <p className="text-sm text-gray-500">
        No Minimal Safe Plans available for this PR.
      </p>
    )

  return (
    <section aria-label="Minimal Safe Plans">
      <h2 className="text-lg font-bold text-gray-900 mb-3">
        Minimal Safe Plans
      </h2>
      <ul className="space-y-3">
        {plans.map((plan) => (
          <li key={plan.plan_id}>
            <MinimalSafePlanCard plan={plan} prId={prId} />
          </li>
        ))}
      </ul>
    </section>
  )
}
