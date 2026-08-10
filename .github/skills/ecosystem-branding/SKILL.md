---
name: ecosystem-branding
description: Protect third-party dependencies across all language ecosystems (Go, Rust, Python, Maven, Gradle) from being renamed or rebranded.
metadata:
  targets: ["go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "requirements.txt", "Pipfile", "Pipfile.lock", "pyproject.toml", "poetry.lock", "pom.xml", "build.gradle"]
  when: "changed file is a Go/Rust/Python/Java dependency manifest"
---

# Ecosystem Branding Guard Skill

The repo's branding (NasTech) applies ONLY to the project's own modules and packages — never to third-party libraries. This skill covers non-JS/non-Docker ecosystems.

## Ground rules
- Dependency **names/identifiers** are immutable in every manifest: go module paths, Cargo crate names, Python distribution names, Maven `groupId:artifactId`, Gradle coordinates.
- Allowed changes: version bumps, `replace`/`override` directives pointing at the same module, lockfile hashes, path changes for vendored copies of the SAME module.
- Forbidden: renaming a module path, swapping crate/distribution names, re-scoping a Python package under `@nastech*`, rewriting `replace` to a branded fork of a third-party library without a human-approved decision.

## Per-ecosystem
- **Go** (`go.mod`/`go.sum`): module paths after `require`/`replace` are identities. A `replace` to a fork is a major change — require approval; never brand a third-party path.
- **Rust** (`Cargo.toml`/`Cargo.lock`): `[dependencies]` keys and `name = "..."` in the lock are identities.
- **Python** (`requirements*.txt`, `Pipfile`, `pyproject.toml`, `poetry.lock`): distribution names (normalized: hyphens/underscores) are identities. `pip`-style extras (`pkg[extra]`) keep the same base name.
- **Java** (`pom.xml`, `build.gradle*`): `groupId:artifactId` pairs are identities.

## Validation
- Re-run the lockfile generator (`go mod tidy`, `cargo build`, `pip-compile`, `poetry lock`, `mvn dependency:resolve`) after any manifest edit and confirm the dependency set is unchanged.
- If BrandGuard refuses a write, STOP and report the blocked identifiers verbatim.
