/**
 * Error hierarchy for @drift-analyzer/sdk.
 *
 * All SDK errors extend DriftSdkError so callers can use a single catch gate:
 *   catch (err) { if (err instanceof DriftSdkError) ... }
 */

// ---------------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------------

export class DriftSdkError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "DriftSdkError";
  }
}

// ---------------------------------------------------------------------------
// Runtime errors (cannot start or find the drift process)
// ---------------------------------------------------------------------------

export class RuntimeNotFoundError extends DriftSdkError {
  constructor(message = "drift runtime not found and bundled bootstrap failed") {
    super(message);
    this.name = "RuntimeNotFoundError";
  }
}

export class BootstrapFailedError extends DriftSdkError {
  public readonly cause: unknown;

  constructor(message: string, cause?: unknown) {
    super(message, cause instanceof Error ? { cause } : undefined);
    this.name = "BootstrapFailedError";
    this.cause = cause;
  }
}

export class RuntimeChecksumError extends DriftSdkError {
  public readonly expected: string;
  public readonly actual: string;

  constructor(expected: string, actual: string) {
    super(`Runtime checksum mismatch — expected ${expected}, got ${actual}`);
    this.name = "RuntimeChecksumError";
    this.expected = expected;
    this.actual = actual;
  }
}

// ---------------------------------------------------------------------------
// Command execution errors
// ---------------------------------------------------------------------------

export class CommandFailedError extends DriftSdkError {
  public readonly exitCode: number;
  public readonly stderr: string;
  public readonly stdout: string;

  constructor(opts: {
    message: string;
    exitCode: number;
    stderr: string;
    stdout: string;
  }) {
    super(opts.message);
    this.name = "CommandFailedError";
    this.exitCode = opts.exitCode;
    this.stderr = opts.stderr;
    this.stdout = opts.stdout;
  }
}

export class CommandTimeoutError extends DriftSdkError {
  public readonly timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`drift command timed out after ${timeoutMs}ms`);
    this.name = "CommandTimeoutError";
    this.timeoutMs = timeoutMs;
  }
}

// ---------------------------------------------------------------------------
// Output parsing errors
// ---------------------------------------------------------------------------

export class InvalidJsonPayloadError extends DriftSdkError {
  public readonly raw: string;

  constructor(raw: string, cause?: unknown) {
    super(
      `drift returned a non-JSON or mixed payload (${raw.slice(0, 80).replace(/\n/g, "\\n")}…)`,
      cause instanceof Error ? { cause } : undefined,
    );
    this.name = "InvalidJsonPayloadError";
    this.raw = raw;
  }
}

export class UnsupportedSchemaVersionError extends DriftSdkError {
  public readonly received: string;
  public readonly supported: string[];

  constructor(received: string, supported: string[]) {
    super(
      `Unsupported drift output schema version "${received}". SDK supports: ${supported.join(", ")}`,
    );
    this.name = "UnsupportedSchemaVersionError";
    this.received = received;
    this.supported = supported;
  }
}
