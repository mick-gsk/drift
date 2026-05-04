interface ErrorBannerProps {
  message: string
  type?: 'error' | 'conflict'
}

export function ErrorBanner({ message, type = 'error' }: ErrorBannerProps) {
  const colours =
    type === 'conflict'
      ? 'bg-amber-50 border-amber-400 text-amber-800'
      : 'bg-red-50 border-red-400 text-red-800'

  const title = type === 'conflict' ? 'Version Conflict' : 'Error'

  return (
    <div
      role="alert"
      className={`rounded-md border px-4 py-3 ${colours}`}
    >
      <span className="font-semibold">{title}: </span>
      {message}
    </div>
  )
}
