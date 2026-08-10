---
name: docker
description: Review Dockerfiles and compose files for correctness, security, and image hygiene.
metadata:
  targets: ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
  when: "changed file is a Dockerfile or docker-compose file"
---

# Docker Review Skill

## What to check
- **Security**: `FROM` images unpinned or from unknown registries, `RUN` as root when not needed, secrets baked via `ENV`/`ARG` (should be build args or secrets mount), `curl | sh` patterns, excessive `--no-install-recommends` missing, `apt-get upgrade` in RUN.
- **Correctness**: wrong `CMD`/`ENTRYPOINT` form (exec vs shell), missing `EXPOSE`/healthcheck, `COPY` after heavy layers (cache invalidation), missing `WORKDIR`, compose `version:` misuse, port/env mismatches with app config.
- **Hygiene**: huge unoptimized images, orphaned build artifacts, missing `.dockerignore` usage, multi-stage build opportunities.
- **Branding**: image references must use the configured org (`nastechairesearch`/`nastechai`) — do NOT flag cosmetic name changes; the branding pipeline owns that.

## What NOT to flag
- Formatting-only changes.
- Suggesting a different base image family without a concrete reason.
- Branding/renaming issues (handled by the separate branding pipeline).

## Severity guidance
- **critical**: image pulls untrusted content, root execution of untrusted binaries, secrets exposed.
- **major**: incorrect runtime config, healthcheck absent where the app needs one, unpinned base.
- **minor**: layer ordering / cache optimization.

## Output
Findings with path, line, severity, category, confidence, message, suggestion.
