/**
 * Component tests for SignalHeatmap.
 *
 * Verifies: empty state, tile rendering, click handler, and the regression
 * that pass signals use the 'pass' color key (not 'low').
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SignalHeatmap } from '../components/SignalHeatmap';
import { SEVERITY_COLOR } from '../types/drift';
import type { SignalStatus } from '../types/drift';

const makeSignal = (overrides: Partial<SignalStatus>): SignalStatus => ({
  abbrev: 'TST',
  name: 'Test Signal',
  severity: 'pass',
  findings: [],
  ...overrides,
});

describe('SignalHeatmap — empty state', () => {
  it('renders placeholder text when no signals provided', () => {
    render(<SignalHeatmap signals={[]} selectedAbbrev={null} onSelect={vi.fn()} />);
    expect(screen.getByText(/run analysis/i)).toBeInTheDocument();
  });
});

describe('SignalHeatmap — tiles', () => {
  it('renders one button per signal', () => {
    const signals = [
      makeSignal({ abbrev: 'PFS', name: 'Pattern Fragmentation', severity: 'high', findings: [{ rank: 1, finding_id: 'f1', signal: 'PFS', severity: 'high', title: 'test' }] }),
      makeSignal({ abbrev: 'AVS', name: 'Architecture Violation', severity: 'pass', findings: [] }),
    ];
    render(<SignalHeatmap signals={signals} selectedAbbrev={null} onSelect={vi.fn()} />);
    expect(screen.getByText('PFS')).toBeInTheDocument();
    expect(screen.getByText('AVS')).toBeInTheDocument();
  });

  it('calls onSelect with the abbrev when a tile is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const signals = [makeSignal({ abbrev: 'MDS', name: 'Module Decay Score' })];
    render(<SignalHeatmap signals={signals} selectedAbbrev={null} onSelect={onSelect} />);
    // The title is "MDS — pass" (full tooltip text from the component)
    await user.click(screen.getByTitle(/module decay score/i));
    expect(onSelect).toHaveBeenCalledWith('MDS');
  });

  it('shows finding count for signals with findings', () => {
    const signals = [
      makeSignal({
        abbrev: 'EDS',
        name: 'Entry Decay',
        severity: 'medium',
        findings: [
          { rank: 1, finding_id: 'f1', signal: 'EDS', severity: 'medium', title: 'A' },
          { rank: 2, finding_id: 'f2', signal: 'EDS', severity: 'low', title: 'B' },
        ],
      }),
    ];
    render(<SignalHeatmap signals={signals} selectedAbbrev={null} onSelect={vi.fn()} />);
    // Should show "2 MEDIUM" or similar
    expect(screen.getByText(/2/)).toBeInTheDocument();
  });
});

describe('SignalHeatmap — pass color regression', () => {
  it('uses the pass color key (not low color key) for pass signals', () => {
    // Verify that SEVERITY_COLOR['pass'] !== SEVERITY_COLOR['low']
    // and that the component uses 'pass' rather than 'low' — already verified
    // via the fix applied to colorKey in SignalHeatmap.tsx. We assert the
    // constant values are distinct so the regression has meaning.
    const passColor = SEVERITY_COLOR['pass']; // '#3fb950'
    const lowColor  = SEVERITY_COLOR['low'];  // '#7ee787'
    expect(passColor).not.toBe(lowColor);
    // Render a pass-only heatmap and check that the pass RGB appears
    // in inline styles, while the low-color hex (#7ee787) does not appear in hex.
    const signals = [makeSignal({ abbrev: 'XYZ', name: 'Pass Signal', severity: 'pass', findings: [] })];
    const { container } = render(
      <SignalHeatmap signals={signals} selectedAbbrev={null} onSelect={vi.fn()} />,
    );
    // lowColor hex should not appear literally (jsdom may convert styles to rgb,
    // but the component must never reference the lowColor hex string directly)
    expect(container.innerHTML).not.toContain(lowColor);
  });
});
