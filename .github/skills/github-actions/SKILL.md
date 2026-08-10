---
name: github-actions
description: Review GitHub Actions workflows for correctness, security, and supply-chain hygiene.
metadata:
  targets: [".github/workflows/*.yml", ".github/workflows/*.yaml"]
  when: "changed file is a GitHub Actions workflow"
---

# GitHub Actions Review Skill

## What to check
- **Security**: actions pinned by tag `@v3` instead of SHA, secrets passed where env-var injection possible, `pull_request_target` used without safety (checkout of untrusted ref), `${{ github.event.pull_request.head.ref }}` in unsafe positions, missing `permissions:` blocks (defaulting to wide perms), untrusted inputs in `run:` without escaping.
- **Correctness**: wrong event triggers, `on:` indentation, missing `if:` conditions that gate on failed steps, `needs` typos, artifacts not uploaded on failure when needed downstream, checkout `fetch-depth` too shallow for diffs.
- **Efficiency**: unnecessary job duplication, missing caching.
- **Consistency**: naming/labels consistent with the rest of the repo's workflow set.

## What NOT to flag
- YAML formatting that the parser accepts.
- Style preferences not affecting behavior/security.

## Severity guidance
- **critical**: action pins by mutable tag, secrets exfiltration path, `pull_request_target` vulnerability.
- **major**: incorrect trigger or condition causing wrong behavior, missing permissions hardening.
- **minor**: efficiency, readability.

## Output
Findings with path, line, severity, category, confidence, message, suggestion.
