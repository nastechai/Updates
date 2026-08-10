---
name: npm-fixer
description: Fix npm dependency, build, and lockfile issues without ever renaming or rebranding dependencies.
metadata:
  extensions: ["package.json", "package-lock.json", "npm-shrinkwrap.json"]
  when: "changed file is an npm manifest or lockfile"
---

# npm Fixer Skill

You fix broken Node/npm projects. The ground rule: **NEVER rename, rebrand, or drop a dependency.** Dependency names are sacred — only their versions, flags, and resolved lockfile entries may change.

## Fix procedure
1. Reproduce: `npm ci` (or `npm install` if no lockfile). Read the error carefully before changing anything.
2. Prefer lockfile-only fixes:
   - stale lockfile -> regenerate with `npm install --package-lock-only` or `npm ci`
   - peer dependency conflict -> `npm install` (allows resolution update) and commit both `package.json` and the lockfile together
   - registry/network flake -> retry, don't rewrite manifests
3. Version issues in `package.json`:
   - `^`/`~` mismatch with installed -> align the range to the installed major/minor; never switch the package to a different one
   - deprecated package flagged by `npm audit` -> bump to the newest version **in the same package**, or add an npm advisory resolution; do NOT swap the dependency for an alternative
4. Security: `npm audit fix` — commit the lockfile changes. If `audit fix` wants to change a dependency name, STOP and leave it to a human.
5. Build/script errors: fix the code or `scripts` in `package.json` — never the `dependencies` block except a pure version bump.

## NEVER do
- Rename a dependency key (e.g. `express` -> `expressjs`) — BrandGuard blocks this; do not try to bypass it.
- Change a package's scoped org (`@nous-research/*` -> something else) — branding is owned by the branding pipeline and validated by `validate-npm-branding.js`.
- Add a brand-new dependency to fix a bug unless the issue explicitly demands it and a human approved.
- Edit `node_modules` or commit a regenerated lockfile whose package names changed.

## Validation
After any manifest change run:
- `node .github/scripts/validate-npm-branding.js` (must exit 0)
- `npm ci && npm test` (or the repo's test command)

## Output
Report exactly which fields changed and confirm no dependency name changed. If BrandGuard or the validator blocks, report the blocker verbatim.
