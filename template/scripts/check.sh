#!/bin/sh
# The project's own checks: lint, format, tests. Project-owned: `copier update` never
# touches it. CI's "Project checks" job and AGENTS.md's Definition of done run it.
# Add each command below; `set -e` fails the run on the first one that fails.
set -eu
cd "$(dirname "$0")/.."

echo "scripts/check.sh: no checks defined yet"
