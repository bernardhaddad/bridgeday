#!/usr/bin/env python3
"""PostToolUse(Edit|Write) hook: lint the file Claude just changed.

Runs whichever linter the project has installed for that file type. Exit 2
feeds the problems back to Claude as the next thing to fix; exit 0 is silent.
Missing tools are not errors: the hook only reports what it could check.
"""

import json
import os
import shutil
import subprocess
import sys

try:
    path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
except Exception:  # noqa: BLE001
    sys.exit(0)
if not path or not os.path.exists(path):
    sys.exit(0)

ext = os.path.splitext(path)[1]
cmds = []
if ext == ".py" and shutil.which("ruff"):
    cmds = [["ruff", "check", path], ["ruff", "format", "--check", path]]
elif (
    ext in (".ts", ".tsx")
    and os.path.exists("tsconfig.json")
    and os.path.isdir("node_modules")
):
    cmds = [["npx", "--no-install", "tsc", "--noEmit", "-p", "."]]
elif ext == ".go" and shutil.which("gofmt"):
    cmds = [["gofmt", "-l", path]]
    if shutil.which("go"):
        cmds.append(["go", "vet", "./..."])

problems = []
for c in cmds:
    try:
        r = subprocess.run(c, capture_output=True, text=True, timeout=90)
    except (subprocess.TimeoutExpired, OSError) as e:  # noqa: PERF203
        problems.append(f"{' '.join(c)}: {e}")
        continue
    out = (r.stdout + r.stderr).strip()
    # gofmt -l prints the file name when it is unformatted and exits 0
    if r.returncode != 0 or (c[0] == "gofmt" and out):
        problems.append(f"$ {' '.join(c)}\n{out[:3000]}")

if problems:
    print(
        "Lint problems in the file you just edited (fix before moving on):\n\n"
        + "\n\n".join(problems),
        file=sys.stderr,
    )
    sys.exit(2)
sys.exit(0)
