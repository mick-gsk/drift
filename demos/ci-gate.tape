Output demos/ci-gate.gif

Set Shell "cmd"
Set FontSize 14
Set Width 1280
Set Height 820
Set Theme "Catppuccin Mocha"
Set Padding 20
Set Framerate 24
Set PlaybackSpeed 1.0

# Step 1: Run full analysis to see findings
Type "echo CI gate — analyze findings first" Sleep 250ms Enter
Sleep 800ms

Type ".venv\\Scripts\\drift.exe analyze --repo examples/demo-project" Sleep 350ms Enter
Sleep 7s

# Step 2: Run the CI check gate against findings
Type "echo Block CI on high-severity findings" Sleep 250ms Enter
Sleep 1000ms

Type ".venv\\Scripts\\drift.exe check --fail-on high" Sleep 350ms Enter
Sleep 7s

# Step 3: Export as SARIF for GitHub Code Scanning
Type "echo Export SARIF for GitHub Code Scanning" Sleep 250ms Enter
Sleep 800ms

Type ".venv\\Scripts\\drift.exe check --fail-on none --format sarif -o drift-findings.sarif && echo SARIF written: drift-findings.sarif" Sleep 350ms Enter
Sleep 4s

Type "type drift-findings.sarif | more" Sleep 200ms Enter
Sleep 3s
Type "del drift-findings.sarif" Sleep 150ms Enter
Sleep 500ms
