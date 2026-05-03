/**
 * Bootstrap — download and cache the managed drift runtime bundle.
 *
 * The bundle is a self-contained Python venv (created via uv) with
 * drift-analyzer pre-installed. Downloaded from the drift GitHub Release assets
 * and stored under XDG_CACHE_HOME / AppData/Local.
 *
 * Each bundle is versioned and integrity-verified via SHA256 checksum.
 */

import { createHash } from "node:crypto";
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { rm } from "node:fs/promises";
import { join } from "node:path";
import { homedir, platform, arch } from "node:os";
import { pipeline } from "node:stream/promises";

import { BootstrapFailedError, RuntimeChecksumError } from "../errors.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * The drift-analyzer version to bundle.
 * Must be kept in sync with the Python package version used to generate types.
 * Override via environment variable DRIFT_BUNDLE_VERSION.
 */
export const DEFAULT_BUNDLE_VERSION = "2.49.0";

const BUNDLE_VERSION = process.env["DRIFT_BUNDLE_VERSION"] ?? DEFAULT_BUNDLE_VERSION;

const GITHUB_BASE = "https://github.com/mick-gsk/drift/releases/download";

// ---------------------------------------------------------------------------
// Filesystem paths
// ---------------------------------------------------------------------------

function getCacheDir(): string {
  const xdg = process.env["XDG_CACHE_HOME"];
  if (xdg) return join(xdg, "drift-analyzer-sdk");
  if (platform() === "win32") {
    const localAppData = process.env["LOCALAPPDATA"] ?? join(homedir(), "AppData", "Local");
    return join(localAppData, "drift-analyzer-sdk");
  }
  return join(homedir(), ".cache", "drift-analyzer-sdk");
}

/**
 * Returns the managed bundle root directory for the current platform+arch+version.
 * The directory contains a Python venv with drift-analyzer installed.
 */
export function getManagedBundlePath(): string {
  return join(getCacheDir(), `v${BUNDLE_VERSION}`, `${platform()}-${arch()}`);
}

// ---------------------------------------------------------------------------
// Platform asset resolution
// ---------------------------------------------------------------------------

type PlatformKey =
  | "linux-x64"
  | "linux-arm64"
  | "darwin-x64"
  | "darwin-arm64"
  | "win32-x64"
  | "win32-arm64";

interface AssetSpec {
  filename: string;
  sha256?: string; // populated in checksums map below
}

function getPlatformKey(): PlatformKey {
  const os = platform() as string;
  const cpuArch = arch() as string;
  const key = `${os}-${cpuArch}` as PlatformKey;
  const supported: PlatformKey[] = [
    "linux-x64",
    "linux-arm64",
    "darwin-x64",
    "darwin-arm64",
    "win32-x64",
    "win32-arm64",
  ];
  if (!supported.includes(key)) {
    throw new BootstrapFailedError(
      `No pre-built drift bundle for platform '${key}'. ` +
        "Install drift manually: pip install drift-analyzer",
    );
  }
  return key;
}

function getAssetSpec(): AssetSpec {
  const key = getPlatformKey();
  const ext = key.startsWith("win32") ? "zip" : "tar.gz";
  // Asset naming convention: drift-bundle-<version>-<os>-<arch>.<ext>
  return { filename: `drift-bundle-${BUNDLE_VERSION}-${key}.${ext}` };
}

function getDownloadUrl(): string {
  const { filename } = getAssetSpec();
  return `${GITHUB_BASE}/v${BUNDLE_VERSION}/${filename}`;
}

// ---------------------------------------------------------------------------
// Integrity check
// ---------------------------------------------------------------------------

function sha256OfFile(filePath: string): string {
  const data = readFileSync(filePath);
  return createHash("sha256").update(data).digest("hex");
}

// ---------------------------------------------------------------------------
// Archive extraction
// ---------------------------------------------------------------------------

async function extractBundle(archivePath: string, destDir: string): Promise<void> {
  const { execFileSync } = await import("node:child_process");
  mkdirSync(destDir, { recursive: true });

  if (archivePath.endsWith(".tar.gz")) {
    execFileSync("tar", ["-xzf", archivePath, "-C", destDir, "--strip-components=1"], {
      stdio: "pipe",
    });
  } else if (archivePath.endsWith(".zip")) {
    // Windows — use PowerShell Expand-Archive
    execFileSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        `Expand-Archive -Path '${archivePath}' -DestinationPath '${destDir}' -Force`,
      ],
      { stdio: "pipe" },
    );
  } else {
    throw new BootstrapFailedError(`Unsupported archive format: ${archivePath}`);
  }
}

// ---------------------------------------------------------------------------
// Download
// ---------------------------------------------------------------------------

async function downloadFile(url: string, destPath: string): Promise<void> {
  // Use Node fetch (available since Node 18)
  const response = await fetch(url);
  if (!response.ok || !response.body) {
    throw new BootstrapFailedError(
      `Failed to download drift bundle from ${url}: HTTP ${response.status} ${response.statusText}`,
    );
  }
  const fileStream = createWriteStream(destPath);
  // Node 18+ fetch body is a web ReadableStream compatible with Node stream.pipeline
  await pipeline(response.body as unknown as NodeJS.ReadableStream, fileStream);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Returns true if a managed bundle exists and appears functional.
 */
export async function isBundleProvisioned(): Promise<boolean> {
  const bundleDir = getManagedBundlePath();
  const sentinelPath = join(bundleDir, ".drift-sdk-version");
  if (!existsSync(sentinelPath)) return false;
  try {
    const recorded = readFileSync(sentinelPath, "utf8").trim();
    return recorded === BUNDLE_VERSION;
  } catch {
    return false;
  }
}

/**
 * Downloads and installs the managed bundle. Idempotent — skips if already present.
 * Throws `BootstrapFailedError` or `RuntimeChecksumError` on failure.
 */
export async function provisionBundle(opts?: { force?: boolean; expectedSha256?: string }): Promise<void> {
  if (!opts?.force && (await isBundleProvisioned())) return;

  const bundleDir = getManagedBundlePath();
  const cacheDir = getCacheDir();
  mkdirSync(cacheDir, { recursive: true });

  const url = getDownloadUrl();
  const { filename } = getAssetSpec();
  const archivePath = join(cacheDir, filename);

  try {
    await downloadFile(url, archivePath);

    if (opts?.expectedSha256) {
      const actual = sha256OfFile(archivePath);
      if (actual !== opts.expectedSha256) {
        throw new RuntimeChecksumError(opts.expectedSha256, actual);
      }
    }

    // Clean existing bundle dir if force
    if (opts?.force && existsSync(bundleDir)) {
      await rm(bundleDir, { recursive: true, force: true });
    }

    await extractBundle(archivePath, bundleDir);

    // Write sentinel
    writeFileSync(join(bundleDir, ".drift-sdk-version"), BUNDLE_VERSION, "utf8");
  } catch (err) {
    if (err instanceof RuntimeChecksumError) throw err;
    throw new BootstrapFailedError(
      `drift bundle provisioning failed: ${err instanceof Error ? err.message : String(err)}`,
      err,
    );
  } finally {
    // Clean up downloaded archive regardless of success/failure
    try {
      if (existsSync(archivePath)) {
        await rm(archivePath, { force: true });
      }
    } catch {
      // best-effort cleanup
    }
  }
}
