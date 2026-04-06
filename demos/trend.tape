Output demos/trend.gif

Set Shell "cmd"
Set FontSize 14
Set Width 1280
Set Height 820
Set Theme "Catppuccin Mocha"
Set Padding 20
Set Framerate 24
Set PlaybackSpeed 1.0

# Show score history over time
Type "echo Drift trend: score history for this repository" Sleep 250ms Enter
Sleep 800ms

Type ".venv\\Scripts\\drift.exe trend --repo . --last 30 2>nul" Sleep 350ms Enter
Sleep 8s

# Show per-module timeline: when and why drift began
Type "echo When did drift begin in each module?" Sleep 250ms Enter
Sleep 1000ms

Type ".venv\\Scripts\\drift.exe timeline --repo . 2>nul" Sleep 350ms Enter
Sleep 8s
