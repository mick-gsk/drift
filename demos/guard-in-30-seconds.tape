# Renders demos/guard.gif — the README hero.
#
#   vhs demos/guard-in-30-seconds.tape
#
# VHS executes the script for real, so whatever ends up in the GIF is whatever
# the guard actually said on the machine that rendered it.

Output demos/guard.gif

Set Shell "bash"
Set FontSize 17
Set Width 1180
Set Height 610
Set Theme "Catppuccin Mocha"
Set Padding 24
Set Framerate 24
Set PlaybackSpeed 1.0
Set TypingSpeed 45ms

Hide
Type "clear" Enter
Show

Sleep 700ms
Type "bash demos/guard-in-30-seconds.sh"
Sleep 500ms
Enter

# The script is fast; these pauses are for the reader, not the guard.
Sleep 6s
Sleep 6s
