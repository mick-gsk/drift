# Troubleshooting

Common issues and how to resolve them.

## Configuration errors

### "Invalid drift config" on startup

Drift validates `drift.yaml` using strict Pydantic schemas. Unknown keys, wrong types, or extra fields cause an immediate error.

**Fix:** Run `drift config validate` to get a detailed error message, then correct the YAML.

```bash
drift config validate --repo .
```

Common causes:

- A signal weight name is misspelled (e.g. `pattern_fragmentaiton` instead of `pattern_fragmentation`)
- An unknown top-level key was added
- A value has the wrong type (e.g. a string where a number is expected)

### Weights sum warning

If your custom weights sum to an unusual value, `drift config validate` will warn. While auto-calibration normalises weights at runtime, extremely skewed values (e.g. summing to 50.0) can distort relative signal importance before calibration runs.

**Fix:** Keep weight sums roughly between 0.5 and 2.0, or rely on the defaults.

## Signal failures

### "Signal 'X' failed; skipping" in verbose output

A single signal failure does not abort the analysis — drift marks the run as *degraded* and continues with the remaining signals.

**Causes:**

- Git history is unavailable or shallow (affects TVS, ECM)
- A very large file triggers a timeout in AST parsing
- An optional dependency (e.g. sentence-transformers for embeddings) is not installed

**Fix:** Check the verbose output (`drift analyze -v`) for the full traceback. Most signal failures are environment issues.

### No findings at all

If `drift analyze` returns zero findings:

1. Check that `include` patterns in `drift.yaml` match your source files (default: `**/*.py`)
2. Check that the repository has enough code — very small repos (< 5 modules) naturally produce fewer signals
3. Run `drift config show` to see the effective configuration

## Performance

### Analysis takes too long

Drift's analysis time scales roughly with files × functions. On very large repositories:

- Use `--path src/` to restrict analysis to a subdirectory
- Set `thresholds.max_discovery_files` in `drift.yaml` (default: 10,000) to cap file enumeration
- Disable embeddings if they are not needed: `embeddings_enabled: false`
- Use `drift check --diff HEAD~1` for incremental CI checks instead of full analysis

### Out of memory

Embedding computation on very large repos (> 5000 functions) can be memory-intensive.

**Fix:** Set `embeddings_enabled: false` in `drift.yaml` or reduce `embedding_batch_size`.

## False positives

### Pattern fragmentation in intentional variant patterns

PFS may flag deliberate architectural patterns (e.g. strategy pattern implementations with multiple handlers) as fragmentation.

**Fix:** Use `# drift:context deliberate-variant` as a comment near the pattern. This applies context dampening (default 0.5×) to the finding's score. Alternatively, use `path_overrides` to suppress PFS for specific paths.

### Architecture violations in test code

Tests often import across layers. This is expected but flagged by AVS.

**Fix:** Add a `path_overrides` section to `drift.yaml`:

```yaml
path_overrides:
  "tests/**":
    exclude_signals:
      - architecture_violation
```

### Low-score findings in small repositories

Repositories with fewer than 15 modules use adaptive dampening to reduce noise. If you still see many low-score findings, raise the `fail_on` threshold:

```yaml
fail_on: high
```

## CI integration

### Exit code 2 instead of 0 or 1

Exit code 2 means drift encountered a runtime error (missing config, unreadable repository, etc.), not a severity gate failure. Check the error message.

| Exit code | Meaning |
|-----------|---------|
| 0 | Analysis passed (no findings above gate) |
| 1 | Findings exceed severity gate |
| 2 | Runtime error |

### SARIF upload fails

Ensure the output is written to a file before uploading:

```bash
drift analyze --format sarif > results.sarif
# then upload results.sarif
```

## Getting help

If none of the above resolves your issue:

1. Run with `-v` for debug logging
2. Check [FAQ](../faq.md) for known limitations
3. Open an issue at [github.com/mick-gsk/drift](https://github.com/mick-gsk/drift/issues)
