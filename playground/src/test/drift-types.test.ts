/**
 * Unit tests for src/types/drift.ts — pure functions and constant completeness.
 *
 * These run without a browser and without Pyodide.
 */
import { describe, it, expect } from 'vitest';
import {
  severityOrder,
  deriveSignalStatuses,
  SEVERITY_COLOR,
  SEVERITY_BG,
  SEVERITY_LABEL,
  type DriftOutput,
  type Severity,
} from '../types/drift';

// ── severityOrder ─────────────────────────────────────────────────────────────

describe('severityOrder', () => {
  it('ranks critical highest', () => {
    expect(severityOrder('critical')).toBeGreaterThan(severityOrder('high'));
  });

  it('ranks pass as 0 (lowest)', () => {
    expect(severityOrder('pass')).toBe(0);
  });

  it('returns 0 for unknown values', () => {
    // @ts-expect-error intentional bad input
    expect(severityOrder('unknown')).toBe(0);
  });

  it('full ordering: critical > high > medium > low > info > pass', () => {
    const order: (Severity | 'pass')[] = ['critical', 'high', 'medium', 'low', 'info', 'pass'];
    for (let i = 0; i < order.length - 1; i++) {
      expect(severityOrder(order[i])).toBeGreaterThan(severityOrder(order[i + 1]));
    }
  });
});

// ── Constant completeness ──────────────────────────────────────────────────────

const ALL_KEYS: (Severity | 'pass')[] = ['critical', 'high', 'medium', 'low', 'info', 'pass'];

describe('SEVERITY_COLOR', () => {
  it.each(ALL_KEYS)('has entry for "%s"', (key) => {
    expect(SEVERITY_COLOR[key]).toBeDefined();
    expect(typeof SEVERITY_COLOR[key]).toBe('string');
  });
});

describe('SEVERITY_BG', () => {
  it.each(ALL_KEYS)('has entry for "%s"', (key) => {
    expect(SEVERITY_BG[key]).toBeDefined();
    expect(typeof SEVERITY_BG[key]).toBe('string');
  });
});

describe('SEVERITY_LABEL', () => {
  it.each(ALL_KEYS)('has entry for "%s"', (key) => {
    expect(SEVERITY_LABEL[key]).toBeDefined();
    expect(typeof SEVERITY_LABEL[key]).toBe('string');
  });
});

// ── deriveSignalStatuses ───────────────────────────────────────────────────────

const makeOutput = (overrides: Partial<DriftOutput> = {}): DriftOutput => ({
  schema_version: '2.2',
  version: '2.0.0',
  repo: '/playground_code',
  analyzed_at: '2026-01-01T00:00:00Z',
  drift_score: 0,
  severity: 'low',
  ...overrides,
});

describe('deriveSignalStatuses', () => {
  it('returns empty array when no findings and no abbrevMap', () => {
    const result = deriveSignalStatuses(makeOutput());
    expect(result).toHaveLength(0);
  });

  it('returns one pass entry per abbrevMap key when no findings', () => {
    const output = makeOutput({
      signal_abbrev_map: { PFS: 'Pattern Fragmentation', AVS: 'Architecture Violation' },
      findings_compact: [],
    });
    const result = deriveSignalStatuses(output);
    expect(result).toHaveLength(2);
    expect(result.every((s) => s.severity === 'pass')).toBe(true);
  });

  it('assigns correct severity from findings', () => {
    const output = makeOutput({
      signal_abbrev_map: { PFS: 'Pattern Fragmentation' },
      findings_compact: [
        {
          rank: 1,
          finding_id: 'f1',
          signal: 'Pattern Fragmentation',
          signal_abbrev: 'PFS',
          severity: 'high',
          title: 'Too many patterns',
        },
      ],
    });
    const [pfs] = deriveSignalStatuses(output);
    expect(pfs.abbrev).toBe('PFS');
    expect(pfs.severity).toBe('high');
    expect(pfs.findings).toHaveLength(1);
  });

  it('picks worst severity across multiple findings for the same signal', () => {
    const output = makeOutput({
      signal_abbrev_map: { EDS: 'Entry Decay Score' },
      findings_compact: [
        {
          rank: 1,
          finding_id: 'f1',
          signal: 'EDS',
          signal_abbrev: 'EDS',
          severity: 'medium',
          title: 'Medium finding',
        },
        {
          rank: 2,
          finding_id: 'f2',
          signal: 'EDS',
          signal_abbrev: 'EDS',
          severity: 'critical',
          title: 'Critical finding',
        },
      ],
    });
    const [eds] = deriveSignalStatuses(output);
    expect(eds.severity).toBe('critical');
    expect(eds.findings).toHaveLength(2);
  });

  it('falls back to signal name when abbrev is absent from signal_abbrev_map', () => {
    const output = makeOutput({
      signal_abbrev_map: {},
      findings_compact: [
        {
          rank: 1,
          finding_id: 'f1',
          signal: 'Mystery Signal',
          signal_abbrev: 'MYS',
          severity: 'low',
          title: 'Something',
        },
      ],
    });
    const result = deriveSignalStatuses(output);
    const mys = result.find((s) => s.abbrev === 'MYS');
    expect(mys).toBeDefined();
    expect(mys!.name).toBe('Mystery Signal');
  });

  it('sorts results by descending severity (critical first)', () => {
    const output = makeOutput({
      signal_abbrev_map: { A: 'Alpha', B: 'Beta', C: 'Gamma' },
      findings_compact: [
        { rank: 1, finding_id: 'f1', signal: 'Beta', signal_abbrev: 'B', severity: 'critical', title: 'B' },
        { rank: 2, finding_id: 'f2', signal: 'Alpha', signal_abbrev: 'A', severity: 'low', title: 'A' },
      ],
    });
    const result = deriveSignalStatuses(output);
    // B (critical) must come before C/A (pass/low)
    const abbrevs = result.map((s) => s.abbrev);
    expect(abbrevs.indexOf('B')).toBeLessThan(abbrevs.indexOf('A'));
  });

  it('uses signal_abbrev key when signal_abbrev field is present', () => {
    const output = makeOutput({
      signal_abbrev_map: { PFS: 'Pattern Fragmentation' },
      findings_compact: [
        {
          rank: 1,
          finding_id: 'f1',
          signal: 'Pattern Fragmentation Score',
          signal_abbrev: 'PFS',
          severity: 'medium',
          title: 'Fragmentation',
        },
      ],
    });
    const result = deriveSignalStatuses(output);
    const pfs = result.find((s) => s.abbrev === 'PFS');
    expect(pfs).toBeDefined();
    expect(pfs!.findings).toHaveLength(1);
  });
});
