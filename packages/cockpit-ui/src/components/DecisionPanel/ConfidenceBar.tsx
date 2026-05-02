interface ConfidenceBarProps {
  confidence: number // 0–1
}

export function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, confidence)) * 100)

  return (
    <div data-testid="confidence-bar" className="w-full">
      <div className="flex justify-between mb-1 text-sm text-gray-600">
        <span>Confidence</span>
        <span className="font-medium">{pct}%</span>
      </div>
      <div className="h-3 w-full rounded-full bg-gray-200 overflow-hidden">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-label={`Confidence ${pct}%`}
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  )
}
