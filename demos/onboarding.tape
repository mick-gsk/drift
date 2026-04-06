Output demos/onboarding.gif

Set Shell "cmd"
Set FontSize 14
Set Width 1280
Set Height 820
Set Theme "Catppuccin Mocha"
Set Padding 20
Set Framerate 24
Set PlaybackSpeed 1.0

# Step 1: Learn what a signal means
Type "echo Learn what drift signals mean" Sleep 250ms Enter
Sleep 800ms

Type ".venv\\Scripts\\drift.exe explain PFS" Sleep 350ms Enter
Sleep 5s

# Step 2: Explore concrete pattern findings
Type "echo Explore pattern findings in your repo" Sleep 250ms Enter
Sleep 1000ms

Type ".venv\\Scripts\\drift.exe patterns --repo examples/demo-project" Sleep 350ms Enter
Sleep 5s

# Step 3: Scaffold config
Type "echo Scaffold drift config for this project" Sleep 250ms Enter
Sleep 800ms

Type ".venv\\Scripts\\drift.exe init --repo examples/demo-project --profile default --dry-run" Sleep 350ms Enter
Sleep 4s
