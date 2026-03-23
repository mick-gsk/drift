Output demos/demo.gif

Set Shell "powershell"
Set FontSize 16
Set Width 1200
Set Height 760
Set Framerate 30
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms

Type "drift self"
Enter
Sleep 3s

Type "drift check --fail-on high"
Enter
Sleep 3s

Type "drift analyze --repo . --format rich"
Enter
Sleep 4s
