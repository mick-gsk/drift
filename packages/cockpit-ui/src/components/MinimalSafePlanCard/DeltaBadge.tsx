interface DeltaBadgeProps {
  label: string
  value: number
}

function formatDelta(v: number): string {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}`
}

export function DeltaBadge({ label, value }: DeltaBadgeProps) {
  const colour =
    value < 0
      ? 'bg-green-100 text-green-700 border-green-200'
      : 'bg-red-100 text-red-700 border-red-200'

  return (
    <span
      data-testid="delta-badge"
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono ${colour}`}
    >
      <span className="text-gray-500">{label}</span>
      <span>{formatDelta(value)}</span>
    </span>
  )
}
