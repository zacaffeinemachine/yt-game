#!/usr/bin/env python3
"""Push local changes to GitHub. Run after editing channels.txt or any other file."""

import subprocess
import sys


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


status = run(['git', 'status', '--porcelain'])
if not status:
    print("Nothing to commit.")
    sys.exit(0)

print("Changed files:")
for line in status.splitlines():
    print(f"  {line}")

run(['git', 'add', '-A'])

msg = input("\nCommit message (press Enter for 'update'): ").strip() or "update"
run(['git', 'commit', '-m', msg])
run(['git', 'push'])

print("Done. GitHub Action will fetch new videos shortly.")
