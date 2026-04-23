import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render errors below the tree and shows a friendly recovery UI
 * instead of a blank white screen. Wraps the entire App in main.tsx.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // In production this could go to an error-reporting service.
    // For now, just log to the console so developers can diagnose.
    console.error('[drift playground] Uncaught render error:', error, info.componentStack);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-drift-bg text-drift-text">
          <div className="flex flex-col items-center gap-4 rounded-xl border border-drift-critical/40 bg-drift-panel px-10 py-8 text-center shadow-2xl">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-drift-critical/40 bg-drift-critical/10 text-2xl text-drift-critical">
              ✕
            </div>
            <div>
              <p className="text-base font-semibold text-drift-text">Something went wrong</p>
              <p className="mt-2 max-w-sm text-sm text-drift-muted">
                {this.state.error?.message ?? 'An unexpected error occurred in the playground.'}
              </p>
            </div>
            <button
              onClick={this.handleReset}
              className="rounded-md border border-drift-border bg-drift-bg px-5 py-2 text-sm font-medium text-drift-text transition-colors hover:border-drift-accent hover:text-drift-accent"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
