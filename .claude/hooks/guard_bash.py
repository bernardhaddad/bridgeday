#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block the handful of commands that must never run here.

Deterministic, so it holds even when the model is sure. Exit 2 = block, and the
message on stderr is shown to Claude so it can pick another route.
"""

import json
import re
import sys

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:  # noqa: BLE001 - never break the session over a malformed payload
    sys.exit(0)

# Heredoc bodies are data (file contents), not commands: drop them before matching.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)", re.S)
cmd = HEREDOC.sub(" ", cmd)

BLOCKED = [
    (
        r"\bgit\s+push\b[^|;&]*\s--force\b(?!-with-lease)",
        "force-push: use --force-with-lease, and only on a branch you own",
    ),
    (
        r"\bgit\s+push\b[^|;&]*\s-f\b",
        "force-push: use --force-with-lease, and only on a branch you own",
    ),
    (
        r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)",
        "destructive git reset/clean: stash or commit first, then ask",
    ),
    (
        r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\$HOME|\.)(\s|$)",
        "recursive delete of a root, home, or the repo",
    ),
    (
        r"\bgit\s+branch\s+-D\b",
        "branch delete with -D: use -d so unmerged work is protected",
    ),
    (r"\bcurl\b.*\|\s*(sudo\s+)?(ba)?sh\b", "piping a download straight into a shell"),
]
for pattern, why in BLOCKED:
    if re.search(pattern, cmd):
        print(
            f"Blocked by .claude/hooks/guard_bash.py: {why}. Command: {cmd[:200]}",
            file=sys.stderr,
        )
        sys.exit(2)
sys.exit(0)
