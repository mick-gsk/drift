# Drift Bot — GitHub App

Automatic architectural drift analysis on every pull request. Install once, get Drift Reports on every PR — no workflow files needed.

## What it does

When a pull request is opened or updated, Drift Bot:

1. Clones the PR branch
2. Runs `drift check --format json`
3. Posts a **Drift Report** comment with score, trend, severity distribution, and top findings
4. Updates the same comment on subsequent pushes (no comment spam)

The comment format matches the [GitHub Action](../action.yml) output, so teams upgrading from the Action get a familiar experience.

## PR Comment Preview

```
## 🏗️ Drift Report

![Drift Score](https://img.shields.io/badge/drift%20score-0.42-yellow?style=flat-square)

| Metric | Value |
|--------|-------|
| **Score** | `0.42` |
| **Trend** | 🟢 -0.030 ▼ improving |
| **Severity** | MEDIUM |
| **Findings** | 12 |
| **Distribution** | HIGH: 2 · MEDIUM: 7 · LOW: 3 |

### Top Findings

| Signal | Finding | Location | Fix |
|--------|---------|----------|-----|
| PFS | 3 patterns for repository initialization | `src/repos.py:45` | Consolidate into factory |
| MDS | Near-duplicate validation logic | `src/api/auth.py:112` | Extract shared validator |
| AVS | Service layer imports from CLI | `src/cli/run.py:8` | Invert dependency |
```

## Setup

### 1. Register the GitHub App

Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App** and configure:

| Setting | Value |
|---------|-------|
| **App name** | Drift Bot (or your preferred name) |
| **Homepage URL** | `https://mick-gsk.github.io/drift/` |
| **Webhook URL** | `https://<your-server>/webhook` |
| **Webhook secret** | Generate a strong random secret |
| **Permissions** | Contents: Read, Pull requests: Write, Metadata: Read |
| **Subscribe to events** | Pull request |

After creation:
- Note the **App ID**
- Generate and download a **private key** (`.pem` file)

### 2. Deploy the server

#### Option A: Fly.io (recommended)

```bash
cd github-app

# First-time setup
fly launch --no-deploy

# Set secrets
fly secrets set GITHUB_APP_ID=123456
fly secrets set GITHUB_WEBHOOK_SECRET=your-webhook-secret
fly secrets set GITHUB_PRIVATE_KEY="$(cat private-key.pem)"

# Deploy
fly deploy
```

Your webhook URL will be `https://drift-bot.fly.dev/webhook`.

#### Option B: Docker (self-hosted)

```bash
cd github-app
docker build -t drift-bot .
docker run -d \
  -p 8000:8000 \
  -e GITHUB_APP_ID=123456 \
  -e GITHUB_WEBHOOK_SECRET=your-webhook-secret \
  -e GITHUB_PRIVATE_KEY_PATH=/keys/private-key.pem \
  -v /path/to/private-key.pem:/keys/private-key.pem:ro \
  drift-bot
```

#### Option C: Any Python host

```bash
cd github-app
pip install -r requirements.txt
export GITHUB_APP_ID=123456
export GITHUB_WEBHOOK_SECRET=your-webhook-secret
export GITHUB_PRIVATE_KEY_PATH=private-key.pem
python -m drift_bot.main
```

### 3. Install on repositories

Go to `https://github.com/apps/<your-app-name>/installations/new` and select the repositories where Drift Bot should run.

Open a PR — the bot will post a Drift Report automatically.

## Architecture

```
GitHub webhook (pull_request)
       │
       ▼
  FastAPI server (drift_bot/main.py)
       │
       ├── Verify HMAC-SHA256 signature
       ├── Get installation access token (JWT → token exchange)
       ├── Clone PR branch (shallow, depth=50)
       ├── Run: drift check --format json --fail-on none
       ├── Format Markdown comment (templates.py)
       └── Upsert PR comment via GitHub API
```

### Files

| File | Purpose |
|------|---------|
| `drift_bot/main.py` | FastAPI app, webhook routing, signature verification |
| `drift_bot/auth.py` | GitHub App JWT creation, installation token exchange |
| `drift_bot/analyzer.py` | Repository cloning, drift analysis, comment posting |
| `drift_bot/templates.py` | PR comment Markdown formatting |
| `app.yml` | GitHub App manifest (permissions, events) |
| `Dockerfile` | Container image for deployment |
| `fly.toml` | Fly.io deployment configuration |

## Security

- **Webhook signature verification**: Every incoming request is verified against the HMAC-SHA256 signature using the webhook secret. Requests with invalid signatures are rejected with 401.
- **Short-lived tokens**: Installation access tokens are generated per-request and expire after 1 hour (GitHub default).
- **Shallow clones**: Repositories are cloned with `--depth=50` and deleted immediately after analysis.
- **No secrets in code**: All credentials are loaded from environment variables.
- **Read-only analysis**: The bot only reads code and posts comments. It cannot push, merge, or modify repository contents.

## Comparison: App vs. Action

| Feature | GitHub Action | Drift Bot App |
|---------|--------------|---------------|
| Setup | Add workflow file per repo | Install app once |
| Identity | `github-actions[bot]` | `drift-bot[bot]` |
| Config needed | `.github/workflows/drift.yml` | None |
| Org-wide | Manual per repo | 1-click for all repos |
| Compute | GitHub-hosted runners | Self-hosted server |
| SARIF upload | ✅ | Not in MVP |
| Drift Brief | ✅ | Not in MVP |

## Configuration

Drift Bot reads `drift.yaml` from the repository root if it exists. No special configuration is needed — the same config format used by the CLI and Action works here.

## Limitations (MVP)

- **No auto-fix PRs** — report-only mode
- **No SARIF upload** — use the GitHub Action for code scanning integration
- **No drift brief** — use the Action with `brief: true` for pre-task briefings
- **Python repos only** — drift analyzes Python codebases
- **No per-repo config override** — uses whatever `drift.yaml` is in the repo

## Development

```bash
cd github-app
pip install -r requirements.txt

# Run locally with ngrok for webhook testing
ngrok http 8000
# Set the ngrok URL as your webhook URL in the GitHub App settings

python -m drift_bot.main
```

## License

Same as the main drift repository — [MIT](../LICENSE).
