import type { DecisionStatus } from '@/types/cockpit'

interface DecisionSelectorProps {
  value: DecisionStatus
  recommendation: DecisionStatus
  onChange: (v: DecisionStatus) => void
}

const OPTIONS: { value: DecisionStatus; label: string }[] = [
  { value: 'go', label: 'Go' },
  { value: 'go_with_guardrails', label: 'Go with Guardrails' },
  { value: 'no_go', label: 'No-Go' },
]

export function DecisionSelector({
  value,
  recommendation,
  onChange,
}: DecisionSelectorProps) {
  return (
    <fieldset>
      <legend className="text-sm font-semibold text-gray-700 mb-2">
        Your Decision
      </legend>
      <div className="flex gap-4">
        {OPTIONS.map((opt) => (
          <label
            key={opt.value}
            data-testid={`decision-option-${opt.value}`}
            className={`flex items-center gap-2 cursor-pointer rounded-lg border px-4 py-2 text-sm transition-colors ${
              value === opt.value
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
            }`}
          >
            <input
              type="radio"
              name="decision"
              value={opt.value}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="sr-only"
            />
            {opt.label}
            {recommendation === opt.value && (
              <span
                className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700"
                title="App recommendation"
              >
                ★
              </span>
            )}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
