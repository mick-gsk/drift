/**
 * Integrity tests for scenario definitions.
 * Pure JS tests — no browser, no Pyodide.
 */
import { describe, it, expect } from 'vitest';
import { SCENARIOS, DEFAULT_SCENARIO_ID, getScenario } from '../scenarios/index';

describe('SCENARIOS data integrity', () => {
  it('has at least one scenario', () => {
    expect(SCENARIOS.length).toBeGreaterThan(0);
  });

  it('all IDs are unique strings', () => {
    const ids = SCENARIOS.map((s) => s.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('every scenario has a non-empty id, label, and description', () => {
    for (const s of SCENARIOS) {
      expect(s.id.trim()).not.toBe('');
      expect(s.label.trim()).not.toBe('');
      expect(s.description.trim()).not.toBe('');
    }
  });

  it('every scenario has at least one file with non-empty content', () => {
    for (const s of SCENARIOS) {
      const files = Object.entries(s.files);
      expect(files.length).toBeGreaterThan(0);
      for (const [name, content] of files) {
        expect(name.trim()).not.toBe('');
        expect(content.trim()).not.toBe('');
      }
    }
  });

  it('all file names are safe (no path separators, no leading dots)', () => {
    for (const s of SCENARIOS) {
      for (const name of Object.keys(s.files)) {
        expect(name).not.toContain('/');
        expect(name).not.toContain('\\');
        expect(name).not.toMatch(/^\./);
      }
    }
  });

  it('DEFAULT_SCENARIO_ID resolves to an existing scenario', () => {
    const found = SCENARIOS.find((s) => s.id === DEFAULT_SCENARIO_ID);
    expect(found).toBeDefined();
  });
});

describe('getScenario', () => {
  it('returns the matching scenario by id', () => {
    const first = SCENARIOS[0];
    expect(getScenario(first.id)).toBe(first);
  });

  it('returns undefined for unknown id', () => {
    expect(getScenario('does-not-exist')).toBeUndefined();
  });
});
