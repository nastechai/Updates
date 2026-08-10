---
name: rust
description: Review Rust code for safety, error handling, and ownership issues.
metadata:
  extensions: [".rs"]
  when: "changed file is a Rust source file"
---

# Rust Review Skill

## What to check
- **Safety**: `unsafe` blocks without clear invariant comments, unchecked `unwrap()`/`expect()` on untrusted data, buffer overflows in manual indexing, integer overflow in release mode.
- **Correctness**: error handling via `?` vs panics, borrow checker workarounds (leaked lifetimes via raw pointers), incorrect `Drop` ordering, iterator invalidation.
- **Concurrency**: `Arc<Mutex<...>>` contention / holding lock across await, data races via `Cell`/`RefCell` across threads, `Send`/`Sync` misuse.
- **Security**: `Command` with untrusted args (no shell), path traversal, deserialization from untrusted input without limits.

## What NOT to flag
- `cargo fmt`/`clippy` style (automated).
- Idiomatic code that differs stylistically from the surrounding crate.

## Severity guidance
- **critical**: UB, data race, panic on untrusted input, security vuln.
- **major**: missing error handling with real consequences, resource leak.
- **minor**: non-idiomatic code, redundant clones (unless hot path).

## Output
Findings with path, line, severity, category, confidence, message, suggestion.
