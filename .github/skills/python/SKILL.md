---
name: python
description: Review Python code for correctness, security, and performance.
metadata:
  extensions: [".py", ".pyw"]
  when: "changed file is a Python source file"
---

# Python Review Skill

## What to check
- **Correctness**: unhandled exceptions, wrong control flow, off-by-one in slices/ranges, swallowed `except:` blocks, missing return.
- **Security**: `eval`/`exec` on untrusted input, `subprocess` with `shell=True` + f-strings, unsafe `yaml.load` without `Loader`, path traversal via `os.path.join` with `..`, SQL built by string concat, hardcoded secrets.
- **Performance**: O(n²) patterns in loops, repeated I/O in loops, missing `with`/resource closure, N+1 DB queries.
- **Concurrency**: shared mutable state across threads, missing locks on counters, `time.sleep` busy-waits.
- **Style**: unused imports/variables, dead code, inconsistent naming vs. the repo's existing modules.

## What NOT to flag
- Cosmetic reformatting (ruff/black/autopep8 territory) unless it breaks the repo's CI.
- Naming/style that already matches the surrounding codebase (consistency wins).
- Speculative refactors with no bug/security/performance impact.
- Missing type hints — unless the file already uses them throughout.

## Severity guidance
- **critical**: exploitable security issue, data loss, or crash on the main path.
- **major**: real bug with clear failure mode, or a genuine security weakness.
- **minor**: maintainability / readability issue with no functional impact.
- **info**: nitpick; omit unless requested.

## Output
Each finding: path, line, severity, category, confidence (0-1), message, and a concrete suggestion snippet when possible. Prefer the smallest fix that matches the Hermes/NasTech codebase style.
