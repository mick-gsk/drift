/**
 * Component tests for LoadingOverlay.
 *
 * Verifies: null render for ready state, loading messages, error state with
 * retry button, and that the retry callback is invoked on click.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoadingOverlay } from '../components/LoadingOverlay';
import type { PyodideStatus } from '../utils/pyodide-runner';

describe('LoadingOverlay — ready state', () => {
  it('renders nothing when status is ready', () => {
    const { container } = render(
      <LoadingOverlay status={{ state: 'ready' }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe('LoadingOverlay — loading states', () => {
  it('shows runtime loading message', () => {
    render(<LoadingOverlay status={{ state: 'loading-runtime', message: 'Downloading Pyodide...' }} />);
    expect(screen.getByText(/loading python runtime/i)).toBeInTheDocument();
    expect(screen.getByText(/pyodide/i)).toBeInTheDocument();
  });

  it('shows drift installation message', () => {
    render(<LoadingOverlay status={{ state: 'installing-drift', message: 'Installing...' }} />);
    // The heading is the shorter string 'Installing drift-analyzer'
    // (the longer description also appears; use exact heading text)
    expect(screen.getByText('Installing drift-analyzer')).toBeInTheDocument();
  });

  it('shows generic initialising message for idle state', () => {
    const status: PyodideStatus = { state: 'idle' };
    render(<LoadingOverlay status={status} />);
    expect(screen.getByText(/initialising/i)).toBeInTheDocument();
  });
});

describe('LoadingOverlay — error state', () => {
  it('shows error heading and message', () => {
    const status: PyodideStatus = {
      state: 'error',
      message: 'Network failure',
    };
    render(<LoadingOverlay status={status} />);
    expect(screen.getByText(/failed to load python runtime/i)).toBeInTheDocument();
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  it('shows retry button when onRetry is provided', () => {
    render(
      <LoadingOverlay
        status={{ state: 'error', message: 'err' }}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('does NOT show retry button without onRetry prop', () => {
    render(<LoadingOverlay status={{ state: 'error', message: 'err' }} />);
    expect(screen.queryByRole('button', { name: /retry/i })).toBeNull();
  });

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <LoadingOverlay
        status={{ state: 'error', message: 'err' }}
        onRetry={onRetry}
      />,
    );
    await user.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
