import type { AccountabilityCluster } from '@/types/cockpit'

interface ClusterNodeProps {
  cluster: AccountabilityCluster
  expanded: boolean
  onToggle: () => void
}

export function ClusterNode({ cluster, expanded, onToggle }: ClusterNodeProps) {
  const pct = Math.round(cluster.risk_share * 100)

  return (
    <div
      data-testid="cluster-node"
      className={`rounded-lg border p-4 cursor-pointer transition-colors ${
        cluster.dominant
          ? 'border-red-400 bg-red-50 ring-2 ring-red-200'
          : 'border-gray-200 bg-white'
      }`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      aria-expanded={expanded ? 'true' : 'false'}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onToggle()
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {cluster.dominant && (
            <span className="text-red-500 font-bold text-xs uppercase tracking-wide">
              Dominant
            </span>
          )}
          <span className="font-medium text-gray-900">{cluster.label}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-sm font-mono font-semibold">{pct}%</span>
            <div className="h-1.5 w-24 rounded-full bg-gray-200 mt-1">
              <div
                className={`h-full rounded-full ${cluster.dominant ? 'bg-red-500' : 'bg-blue-400'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <span className="text-gray-400 text-sm">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>
    </div>
  )
}
