---
name: shell
description: Review shell scripts for correctness, safety, and portability.
metadata:
  extensions: [".sh", ".bash"]
  when: "changed file is a shell script"
---

# Shell Review Skill

## What to check
- **Correctness**: unquoted variables (word splitting/glob expansion), `set -e` missing where needed, incorrect `[ ]` vs `[[ ]]`, pipefail not set when exit codes matter, wrong operator precedence in conditions.
- **Security**: `eval` on untrusted input, `$@`/`$1` used in `eval` or `sh -c`, `curl|sh` from non-pinned sources, secrets on the command line (visible in `ps`), reading secrets from world-readable files, symlink races in temp-dir usage.
- **Portability**: bashisms in `#!/bin/sh` scripts, reliance on GNU-only tools without checking.
- **Robustness**: missing `set -u`, unsafe temp file creation (`mktemp`), unhandled failures in loops.

## What NOT to flag
- `shellcheck`-only stylistic findings already covered by tooling.
- Trailing-whitespace/formatting issues.

## Severity guidance
- **critical**: command injection, secret leakage, `eval` of untrusted data.
- **major**: unquoted variable with spaces that will break, missing failure handling that hides errors.
- **minor**: portability/style.

## Output
Findings with path, line, severity, category, confidence, message, suggestion.
