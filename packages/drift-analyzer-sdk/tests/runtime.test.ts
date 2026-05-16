/**
 * Unit tests for the runtime resolver.
 * All external I/O is mocked via vi.mock — no real child_process spawning.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock node:child_process at the top so all tests share the mock
vi.mock("node:child_process", () => ({
  execSync: vi.fn(),
  execFile: vi.fn(),
}));

// Mock node:fs to prevent real filesystem access
vi.mock("node:fs", () => ({
  existsSync: vi.fn(() => false),
  mkdirSync: vi.fn(),
  readFileSync: vi.fn(() => ""),
  writeFileSync: vi.fn(),
  createWriteStream: vi.fn(),
}));

// Mock bootstrap to avoid real download logic
vi.mock("../src/runtime/bootstrap.js", () => ({
  isBundleProvisioned: vi.fn(async () => false),
  getManagedBundlePath: vi.fn(() => "/fake/bundle"),
}));

describe("runtime resolver", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env["DRIFT_BIN"];
  });

  afterEach(() => {
    delete process.env["DRIFT_BIN"];
  });

  it("resolves to DRIFT_BIN when set and file exists", async () => {
    const fakeBin = "/usr/local/bin/drift-fake";
    process.env["DRIFT_BIN"] = fakeBin;

    const { existsSync } = await import("node:fs");
    const { execSync } = await import("node:child_process");

    vi.mocked(existsSync).mockImplementation((p: unknown) => p === fakeBin);
    vi.mocked(execSync).mockReturnValue("drift 2.49.0\n" as unknown as Buffer);

    // Re-import resolver after mocks are set
    const { resolveRuntime } = await import("../src/runtime/resolver.js");
    const result = await resolveRuntime();

    expect(result.executablePath).toBe(fakeBin);
    expect(result.runtimeSource).toBe("path");
  });

  it("resolveRuntime throws RuntimeNotFoundError when nothing is found", async () => {
    delete process.env["DRIFT_BIN"];

    const { existsSync } = await import("node:fs");
    const { execSync } = await import("node:child_process");

    vi.mocked(existsSync).mockReturnValue(false);
    vi.mocked(execSync).mockImplementation(() => {
      throw new Error("command not found");
    });

    const { resolveRuntime } = await import("../src/runtime/resolver.js");
    const { RuntimeNotFoundError } = await import("../src/errors.js");

    await expect(resolveRuntime()).rejects.toThrowError(RuntimeNotFoundError);
  });

  it("queryHealth returns ok:false on error", async () => {
    delete process.env["DRIFT_BIN"];

    const { existsSync } = await import("node:fs");
    const { execSync } = await import("node:child_process");

    vi.mocked(existsSync).mockReturnValue(false);
    vi.mocked(execSync).mockImplementation(() => {
      throw new Error("command not found");
    });

    const { queryHealth } = await import("../src/runtime/resolver.js");
    const health = await queryHealth();

    expect(health.ok).toBe(false);
    expect(health.version).toBeNull();
    expect(health.error).toBeDefined();
  });
});
