'use client'

import { useEffect, useState } from 'react'
import { fetchClusters } from '@/api/client'
import type { AccountabilityCluster } from '@/types/cockpit'
import { ClusterNode } from './ClusterNode'
import { ClusterFileList } from './ClusterFileList'
import { ErrorBanner } from '@/components/ErrorBanner'

interface AccountabilityGraphProps {
  prId: string
}

export function AccountabilityGraph({ prId }: AccountabilityGraphProps) {
  const [clusters, setClusters] = useState<AccountabilityCluster[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchClusters(prId)
      .then((data) =>
        // Sort descending by risk_share
        [...data].sort((a, b) => b.risk_share - a.risk_share),
      )
      .then(setClusters)
      .catch((e: Error) => setError(e.message))
  }, [prId])

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  if (error) return <ErrorBanner message={error} />

  return (
    <section aria-label="Accountability Graph">
      <h2 className="text-lg font-bold text-gray-900 mb-3">
        Risk Cluster Graph
      </h2>
      <ul className="space-y-2">
        {clusters.map((cluster) => (
          <li key={cluster.cluster_id}>
            <ClusterNode
              cluster={cluster}
              expanded={expanded.has(cluster.cluster_id)}
              onToggle={() => toggle(cluster.cluster_id)}
            />
            {expanded.has(cluster.cluster_id) && (
              <ClusterFileList files={cluster.files} />
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
