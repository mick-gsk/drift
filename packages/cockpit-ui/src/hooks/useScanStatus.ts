'use client'

import { useEffect, useRef, useState } from 'react'
import { fetchScanStatus } from '@/api/client'
import type { ScanStatus } from '@/types/cockpit'

interface UseScanStatusResult {
  status: ScanStatus
  progress: number
}

const POLL_INTERVAL_MS = 3000

export function useScanStatus(prId: string): UseScanStatusResult {
  const [status, setStatus] = useState<ScanStatus>('not_started')
  const [progress, setProgress] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!prId) return

    const poll = async () => {
      try {
        const res = await fetchScanStatus(prId)
        setStatus(res.status)
        setProgress(res.progress)
        if (res.status === 'complete') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      } catch {
        // silently ignore poll errors; parent handles via panel fetch error
      }
    }

    poll()
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [prId])

  return { status, progress }
}
