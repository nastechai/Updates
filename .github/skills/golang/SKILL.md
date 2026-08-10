---
name: golang
description: Review Go code for correctness, concurrency safety, and idiomatic errors.
metadata:
  extensions: [".go"]
  when: "changed file is a Go source file"
---

# Go Review Skill

## What to check
- **Correctness**: ignored errors, shadowed variables, wrong `defer` scope (loop defer accumulation), incorrect slice bounds, map iteration order assumptions.
- **Concurrency**: data races on shared maps/slices, channel deadlock/close-while-send, `sync.WaitGroup` misuse (Add after Wait), missing mutex around shared state, goroutine leaks.
- **Security**: `exec.Command` with user input, unsafe reflection, SQL/HTML injection, integer overflow in size/parsing math, weak crypto (`crypto/md5` for auth, `math/rand` for security).
- **Idiom**: missing `error` returns, `panic` in library code, using `interface{}` where a typed value exists.

## What NOT to flag
- `gofmt`/`go vet` formatting (automated).
- Naming that matches existing packages.
- Performance micro-optimizations without benchmarks.

## Severity guidance
- **critical**: data race, deadlock, security vuln, panic on main path.
- **major**: ignored error with real consequences, goroutine leak.
- **minor**: non-idiomatic code, dead code.

## Output
Findings with path, line, severity, category, confidence, message, suggestion. Follow existing package conventions.
