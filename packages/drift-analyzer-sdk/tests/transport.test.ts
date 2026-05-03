/**
 * Unit tests for the transport layer.
 * Tests: extractJsonPayload, parseJsonPayload, injection guard.
 */

import { describe, it, expect } from "vitest";
import { extractJsonPayload, parseJsonPayload } from "../src/transport/process.js";
import { InvalidJsonPayloadError, UnsupportedSchemaVersionError } from "../src/errors.js";

// ---------------------------------------------------------------------------
// extractJsonPayload
// ---------------------------------------------------------------------------

describe("extractJsonPayload", () => {
  it("extracts pure JSON untouched", () => {
    const json = '{"a": 1}';
    expect(extractJsonPayload(json)).toBe(json);
  });

  it("strips Rich trailing symbols after closing brace", () => {
    const json = '{"a": 1}';
    const raw = json + "\n\u2714 Analysis complete";
    expect(extractJsonPayload(raw)).toBe(json);
  });

  it("strips Rich header before opening brace", () => {
    const raw = "\u2714 Starting analysis…\n{\"b\": 2}";
    expect(extractJsonPayload(raw)).toBe('{"b": 2}');
  });

  it("throws InvalidJsonPayloadError when no JSON braces found", () => {
    expect(() => extractJsonPayload("no json here")).toThrowError(InvalidJsonPayloadError);
  });

  it("throws when start > end", () => {
    // malformed — closing brace before opening brace in weird string
    expect(() => extractJsonPayload("}garbage{")).toThrowError(InvalidJsonPayloadError);
  });
});

// ---------------------------------------------------------------------------
// parseJsonPayload
// ---------------------------------------------------------------------------

const validOutput = {
  schema_version: "2.2",
  version: "2.49.0",
  repo: "/tmp/test",
  analyzed_at: "2025-01-01T00:00:00Z",
  drift_score: 0.42,
  severity: "medium",
};

describe("parseJsonPayload", () => {
  it("parses valid JSON with supported schema version", () => {
    const result = parseJsonPayload<typeof validOutput>(JSON.stringify(validOutput));
    expect(result.schema_version).toBe("2.2");
    expect(result.drift_score).toBe(0.42);
  });

  it("passes through JSON without schema_version field", () => {
    const partial = { version: "2.49.0", repo: "/tmp/test" };
    const result = parseJsonPayload<typeof partial>(JSON.stringify(partial));
    expect(result.version).toBe("2.49.0");
  });

  it("strips ANSI sequences before parsing", () => {
    const withAnsi = "\x1b[32m" + JSON.stringify(validOutput) + "\x1b[0m";
    const result = parseJsonPayload<typeof validOutput>(withAnsi);
    expect(result.drift_score).toBe(0.42);
  });

  it("throws UnsupportedSchemaVersionError for future version", () => {
    const future = { ...validOutput, schema_version: "9.0" };
    expect(() => parseJsonPayload(JSON.stringify(future))).toThrowError(
      UnsupportedSchemaVersionError,
    );
  });

  it("throws InvalidJsonPayloadError for malformed JSON", () => {
    expect(() => parseJsonPayload("{not valid json}")).toThrowError(InvalidJsonPayloadError);
  });

  it("throws InvalidJsonPayloadError when no JSON braces present", () => {
    expect(() => parseJsonPayload("plain text")).toThrowError(InvalidJsonPayloadError);
  });
});
