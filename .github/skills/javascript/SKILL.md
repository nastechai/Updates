---
name: javascript
description: Review JavaScript/TypeScript code for correctness, security, and performance.
metadata:
  extensions: [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]
  when: "changed file is a JS/TS source file"
---

# JavaScript / TypeScript Review Skill

## What to check
- **Correctness**: async/await misuse (fire-and-forget promises, missing await), `undefined`/`null` handling, incorrect equality (`==` vs `===`), mutation of props/state in React, stale closures in effects/handlers.
- **Security**: `eval`/`new Function` on untrusted input, XSS via `dangerouslySetInnerHTML`/`innerHTML`, prototype pollution via unsafe merge, SSRF in fetch targets, secrets in client bundles.
- **Performance**: work in render loops, missing memoization on hot paths, unbounded array/object growth, blocking main thread with sync loops.
- **TypeScript**: `any` used to bypass type errors, unsafe type assertions, missing error handling in `try/catch`.

## What NOT to flag
- Prettier/eslint-only formatting.
- Style matching the surrounding code.
- Suggesting a dependency rewrite (e.g., "use X instead of Y framework").

## Severity guidance
- **critical**: exploitable vuln (XSS, SSRF, prototype pollution), crash, data leak.
- **major**: real bug with clear failure, unhandled promise rejection on a main path.
- **minor**: maintainability, naming, dead code.
- **info**: nitpick.

## Output
Findings with path, line, severity, category, confidence, message, suggestion. Match the repo's existing import/format conventions.
