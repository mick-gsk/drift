/**
 * Unit tests for the error hierarchy.
 */

import { describe, it, expect } from "vitest";
import {
  DriftSdkError,
  RuntimeNotFoundError,
  BootstrapFailedError,
  RuntimeChecksumError,
  CommandFailedError,
  CommandTimeoutError,
  InvalidJsonPayloadError,
  UnsupportedSchemaVersionError,
} from "../src/errors.js";

describe("error hierarchy", () => {
  it("all errors are instances of DriftSdkError", () => {
    const errors = [
      new RuntimeNotFoundError(),
      new BootstrapFailedError("test"),
      new RuntimeChecksumError("expected", "actual"),
      new CommandFailedError({ message: "failed", exitCode: 1, stderr: "", stdout: "" }),
      new CommandTimeoutError(5000),
      new InvalidJsonPayloadError("raw"),
      new UnsupportedSchemaVersionError("9.0", ["2.2"]),
    ];
    for (const err of errors) {
      expect(err).toBeInstanceOf(DriftSdkError);
      expect(err).toBeInstanceOf(Error);
    }
  });

  it("RuntimeChecksumError exposes expected and actual", () => {
    const err = new RuntimeChecksumError("abc", "def");
    expect(err.expected).toBe("abc");
    expect(err.actual).toBe("def");
    expect(err.message).toContain("abc");
    expect(err.message).toContain("def");
  });

  it("CommandFailedError exposes exitCode, stderr, stdout", () => {
    const err = new CommandFailedError({
      message: "failed",
      exitCode: 2,
      stderr: "err output",
      stdout: "some output",
    });
    expect(err.exitCode).toBe(2);
    expect(err.stderr).toBe("err output");
    expect(err.stdout).toBe("some output");
  });

  it("CommandTimeoutError exposes timeoutMs", () => {
    const err = new CommandTimeoutError(3000);
    expect(err.timeoutMs).toBe(3000);
    expect(err.message).toContain("3000");
  });

  it("UnsupportedSchemaVersionError exposes received and supported", () => {
    const err = new UnsupportedSchemaVersionError("99.0", ["2.0", "2.1", "2.2"]);
    expect(err.received).toBe("99.0");
    expect(err.supported).toEqual(["2.0", "2.1", "2.2"]);
  });

  it("InvalidJsonPayloadError exposes the raw payload", () => {
    const raw = "some garbage { not json";
    const err = new InvalidJsonPayloadError(raw);
    expect(err.raw).toBe(raw);
  });

  it("error names match class names", () => {
    expect(new RuntimeNotFoundError().name).toBe("RuntimeNotFoundError");
    expect(new BootstrapFailedError("x").name).toBe("BootstrapFailedError");
    expect(new RuntimeChecksumError("a", "b").name).toBe("RuntimeChecksumError");
    expect(new CommandTimeoutError(1).name).toBe("CommandTimeoutError");
    expect(new InvalidJsonPayloadError("r").name).toBe("InvalidJsonPayloadError");
    expect(new UnsupportedSchemaVersionError("x", []).name).toBe("UnsupportedSchemaVersionError");
  });
});
