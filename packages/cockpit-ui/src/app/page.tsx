'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { parsePrUrl } from '@/api/client'

export default function HomePage() {
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const result = parsePrUrl(url.trim())
    if (!result) {
      setError(
        'Invalid GitHub PR URL. Expected format: https://github.com/owner/repo/pull/123',
      )
      return
    }
    setError(null)
    const { owner, repo, pr_number } = result
    router.push(`/cockpit/${owner}/${repo}/${pr_number}`)
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Drift Cockpit
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            Paste a GitHub PR URL to open the decision cockpit.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="pr-url"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                GitHub PR URL
              </label>
              <input
                id="pr-url"
                data-testid="pr-url-input"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo/pull/123"
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              {error && (
                <p
                  data-testid="url-error"
                  className="mt-1 text-xs text-red-600"
                >
                  {error}
                </p>
              )}
            </div>
            <button
              type="submit"
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              Open Cockpit
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}
