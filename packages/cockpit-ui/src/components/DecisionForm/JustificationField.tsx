import type { ChangeEventHandler } from 'react'

interface JustificationFieldProps {
  value: string
  required: boolean
  onChange: ChangeEventHandler<HTMLTextAreaElement>
}

export function JustificationField({
  value,
  required,
  onChange,
}: JustificationFieldProps) {
  return (
    <div>
      <label
        htmlFor="justification"
        className="block text-sm font-medium text-gray-700 mb-1"
      >
        Justification
        {required && <span className="ml-1 text-red-500">*</span>}
      </label>
      <textarea
        id="justification"
        data-testid="justification-field"
        value={value}
        onChange={onChange}
        required={required}
        rows={3}
        className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 ${
          required && !value.trim()
            ? 'border-red-400 bg-red-50'
            : 'border-gray-300'
        }`}
        placeholder={
          required
            ? 'Required: explain why this differs from the recommendation'
            : 'Optional justification'
        }
      />
    </div>
  )
}
