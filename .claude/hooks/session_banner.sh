#!/usr/bin/env bash
# SessionStart: one line so Claude does not start cold.
# Shows the project's spec/plan status when docs/ exists, the latest Claude
# ecosystem digest when docs/claude-updates exists, and the mastery commands.
line=""
if [ -f docs/spec.md ]; then
  spec=$(sed -n '1s/^# //p' docs/spec.md)
  open=$(grep -c '^- \[ \]' docs/plan.md 2>/dev/null); open=${open:-0}
  done_=$(grep -c '^- \[x\]' docs/plan.md 2>/dev/null); done_=${done_:-0}
  line="Project: ${spec:-untitled}. Plan: ${done_} done, ${open} open (docs/plan.md)."
fi
f=$(ls -1 docs/claude-updates/20*.md 2>/dev/null | sort | tail -1)
if [ -n "$f" ]; then
  line="$line Latest Claude digest: $f."
fi
echo "${line:-No docs/spec.md here.} One command: /mastery:do <anything> (in this workspace: /do)."
