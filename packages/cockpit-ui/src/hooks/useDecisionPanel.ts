'use client'

import { useCallback, useEffect, useState } from 'react'
import { fetchDecisionPanel, ApiError } from '@/api/client'
import { useScanStatus } from './useScanStatus'
import type { DecisionPanel } from '@/types/cockpit'

interface UseDecisionPanelResult {
  panel: DecisionPanel | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useDecisionPanel(prId: string): UseDecisionPanelResult {
  const [panel, setPanel] = useState<DecisionPanel | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { status: scanStatus } = useScanStatus(prId)

  const load = useCallback(async () => {
    if (!prId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDecisionPanel(prId)
      setPanel(data)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError('not_found')
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Unknown error')
      }
    } finally {
      setLoading(false)
    }
  }, [prId])

  // Reload panel when scan completes
  useEffect(() => {
    if (scanStatus === 'complete') {
      load()
    }
  }, [scanStatus, load])

  useEffect(() => {
    load()
  }, [load])

  return { panel, loading, error, refetch: load }
}
