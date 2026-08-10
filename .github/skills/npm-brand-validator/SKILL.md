---
name: npm-brand-validator
description: Verify npm branding NEVER touches third-party dependencies — only the project's own package identity may carry NasTech branding.
metadata:
  targets: ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".npmrc", "bower.json", "composer.json"]
  when: "changed file is an npm/JS dependency manifest or lockfile"
---

# npm Brand Validator Skill

Purpose: guarantee the repo's branding (NasTech) is applied ONLY to the project's own identity and never to third-party dependencies.

## Identity model
- Project-owned branded strings (may contain brand marks): package `name`, `description`, `keywords`, `repository`, `bugs`, `homepage`, `.npmrc` scopes, and the project's own scoped packages (e.g. `@nastech-research/*`).
- Third-party dependencies (must NEVER be branded, renamed, or re-scoped): everything under `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`, and every resolved package in `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml`.

## Checks (run `node .github/scripts/validate-npm-branding.js`)
1. Any dependency key containing a brand token (nastech, nastechai, nous) that is NOT the project's own scope -> violation.
2. Any lockfile `packages[node_modules/...]` entry whose `name` or key gained a brand token -> violation (transitive deps are owned by upstream; re-scoping them breaks installs).
3. A project-branded package name must match the configured org/scope exactly — no partial/trailing renames.
4. `.npmrc` scope mapping must point to the correct registry; never re-scope a third-party registry.

## What a fix looks like
- Own identity fields: safe to normalize brand spelling (the branding pipeline owns this; if you are NOT the branding pipeline, only report).
- A third-party dep that was mistakenly renamed: revert the name to the canonical upstream name and restore the lockfile.

## Failures
- If the validator exits non-zero or BrandGuard refuses a write, STOP. Report the violation paths verbatim. Do not attempt to silence the guard.
