---
name: docker-brand-validator
description: Verify Docker branding NEVER rewrites third-party images or registry refs — only owned nastechairesearch/nastechai images may carry the brand.
metadata:
  targets: ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore", ".docker/config.json"]
  when: "changed file is a Dockerfile, compose file, or docker config"
---

# Docker Brand Validator Skill

Purpose: guarantee container branding touches ONLY images the org owns, and never third-party base images, registries, or public tools.

## Identity model
- Owned (may carry the brand): images under the org's registries (`nastechairesearch/*`, `nastechai/*`), the project's own image names, `NASTECH_*` env vars, `/opt/nastech` paths, and the project's own `docker-compose` service images.
- Third-party (must NEVER be rewritten): `FROM` base images (`python`, `node`, `alpine`, `nvidia/cuda`, `ghcr.io/*`, `gcr.io/*`, `quay.io/*`, Docker Hub library images), any `image:` in compose pointing outside the org, `.dockerignore` patterns, and action refs in workflows that point at upstream GitHub Actions.

## Checks (run `bash .github/scripts/validate-docker-branding.sh`)
1. A third-party `FROM` image renamed to a branded name -> violation (breaks reproducibility + supply-chain provenance).
2. A third-party `image:` in compose renamed -> violation.
3. Branded `nastechairesearch/*` refs must keep exact org spelling — no `nastechai`/`nastechairesearch` mixing, no partial renames (`nastech` alone).
4. `.dockerignore` and registry config must not lose or rewrite third-party references.
5. `NASTECH_*` env/path renames in owned images are fine (branding pipeline territory).

## What a fix looks like
- Revert a misbranded third-party base image to its canonical upstream ref (keep tag pin).
- Restore the original registry for a pulled artifact (e.g. `gcr.io/...` -> don't brand).

## Failures
- If `validate-docker-branding.sh` exits non-zero or BrandGuard blocks the write, STOP and report the exact line. Never rewrite `FROM`/`image:` to silence the guard.
