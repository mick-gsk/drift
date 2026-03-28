# Package KPI example dataset

This folder contains a minimal synthetic dataset for the monthly package KPI script.

For real project counts, the repository now supports a public-data flow:
- derive usage events from public GitHub repositories that declare the package dependency
- merge this with PyPI monthly downloads
- compute MAUP per month from these real, project-keyed events

## Files

- usage.csv: usage events with timestamp, project_id, version
- defects.csv: defect events with confirmed/fixed timestamps and severity
- kpi-thresholds.json: green/yellow/red KPI policy for monthly status evaluation

## Run

From repository root:

```bash
python scripts/package_kpis.py \
  --package drift-analyzer \
  --usage-csv examples/package-kpis/usage.csv \
  --defects-csv examples/package-kpis/defects.csv \
  --currency-versions 1.4.1,1.4.0 \
  --thresholds-json examples/package-kpis/kpi-thresholds.json \
  --months 12 \
  --output benchmark_results/package_kpis_example.json
```

The output JSON contains one KPI row per month.

## Track real PyPI downloads

Fetch real monthly downloads from PyPIStats:

```bash
python scripts/fetch_pypistats.py \
  --package drift-analyzer \
  --months 12 \
  --output benchmark_results/package_kpis/pypi_downloads_monthly.csv
```

Merge these downloads into KPI output (requires real usage.csv):

```bash
python scripts/package_kpis.py \
  --package drift-analyzer \
  --usage-csv path/to/real/usage.csv \
  --defects-csv path/to/real/defects.csv \
  --downloads-csv benchmark_results/package_kpis/pypi_downloads_monthly.csv \
  --thresholds-json examples/package-kpis/kpi-thresholds.json \
  --months 12 \
  --output benchmark_results/package_kpis/package_kpis_real.json
```

When thresholds are enabled, each monthly KPI row includes a `status` object with
`green`, `yellow`, `red`, or `no-data` per metric.

## Derive real monthly project usage from public GitHub data

Create project-keyed usage events from public dependency declarations:

```bash
python scripts/fetch_github_usage.py \
  --package drift-analyzer \
  --max-pages 5 \
  --output benchmark_results/package_kpis/github_usage_events.csv
```

Then compute monthly MAUP from this real usage source:

```bash
python scripts/package_kpis.py \
  --package drift-analyzer \
  --usage-csv benchmark_results/package_kpis/github_usage_events.csv \
  --downloads-csv benchmark_results/package_kpis/pypi_downloads_monthly.csv \
  --thresholds-json examples/package-kpis/kpi-thresholds.json \
  --months 12 \
  --output benchmark_results/package_kpis/package_kpis_real.json
```

Scope note: these MAUP values are exact within the measured source scope
(public GitHub repositories with detectable dependency declarations).
