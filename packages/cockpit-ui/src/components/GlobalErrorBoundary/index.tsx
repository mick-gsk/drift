'use client'

import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string | null
}

export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message ?? 'An error occurred' }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Intentionally silent — no external logging in static frontend
    void error
    void info
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen items-center justify-center p-8"
        >
          <div className="max-w-lg rounded-xl border border-red-200 bg-red-50 p-8 text-center">
            <h1 className="text-xl font-bold text-red-700 mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-red-600 mb-4">{this.state.message}</p>
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, message: null })}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
