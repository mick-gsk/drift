interface LoadingIndicatorProps {
  progress?: number
}

export function LoadingIndicator({ progress }: LoadingIndicatorProps) {
  const pct = progress != null ? Math.min(100, Math.max(0, progress)) : null

  return (
    <div
      aria-label="Scan in progress"
      aria-live="polite"
      className="w-full"
    >
      <div className="flex items-center justify-between mb-1 text-sm text-gray-600">
        <span>Drift scan running…</span>
        {pct !== null && <span>{pct}%</span>}
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
        {pct !== null ? (
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        ) : (
          <div className="h-full rounded-full bg-blue-400 animate-pulse w-full" />
        )}
      </div>
    </div>
  )
}
