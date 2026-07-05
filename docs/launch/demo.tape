# Plumbline launch demo — VHS tape (https://github.com/charmbracelet/vhs)
#
# Produces `plumbline-demo.gif`: a real, reproducible scan of simonw/llm at the
# pinned commit. Because VHS runs the command live in a headless terminal, the
# GIF always shows the *actual* current output — regenerate it whenever the rule
# set changes and the numbers stay honest. This is why we ship a tape, not a
# hand-recorded cast.
#
# ── One-time prep (in the directory you'll run `vhs` from) ───────────────────
#   brew install vhs ffmpeg ttyd           # vhs + its deps
#   pipx install actaclad-plumbline        # `plumb` on PATH (or: uv tool install)
#   git clone https://github.com/simonw/llm.git
#   git -C llm checkout 0d593ea            # the pinned commit the launch copy cites
#
# ── Record ───────────────────────────────────────────────────────────────────
#   vhs docs/launch/demo.tape              # -> plumbline-demo.gif  (attach to blog / X tweet 3)
#
# Verified 2026-07-05 against plumb 0.0.1 (32 rules): 3 findings, Readiness 93/100.
# If you re-run on a later Plumbline, eyeball the output and update the launch copy.
#
# The scan's last line tips `--open` (the branded HTML report). VHS records only
# the terminal, so the report itself needs a separate QuickTime screen-rec of
# `plumb scan ./llm --open` (browser) — see demo-script.md Beat 3.5.

Output plumbline-demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 760
Set Padding 24
Set TypingSpeed 55ms
Set Theme "Catppuccin Mocha"
# (Swap the theme for an ActaClad black/gold palette if you want brand match —
#  a named dark theme is used here for a reliable render.)

# Clean prompt, no scrollback.
Hide
Type "PS1='$ '" Enter
Type "clear" Enter
Show

# The one non-negotiable beat: point it at a real, well-built tool, cold.
Type "plumb scan ./llm"
Sleep 800ms
Enter

# Let the findings + the Readiness score render, then hold on the punchline
# (3 findings on a good codebase, no 200-line wall — Readiness 93/100).
Sleep 5s
Sleep 3s
