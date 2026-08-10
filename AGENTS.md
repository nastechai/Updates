# AGENTS.md — NasTech Update Pipeline Rules

Rules for AI coding assistants, agents, and bots working in **nastechai/Updates**.
Every agent (auto-fixer, review, brand, sync, pipeline) MUST follow these rules.

---

## 1. What this repo is

`nastechai/Updates` is the **automation/pipeline control repo**. It ingests
upstream code from **NousResearch/hermes-agent**, rebrands it to NasTech,
fixes dependencies, verifies it, and finally delivers ALL fixes to
**nastechai/nastech-agent** as a PR. `main` is the HEAD of the pipeline and
holds the control system (workflows, scripts, rules).

## 2. The ordered pipeline — 10 branches, main = HEAD

Promotion order (bottom = upstream source, top = HEAD). **Every stage runs
STRICTLY AFTER the previous one — never in parallel.** Stage N waits for
Stage N−1's checks to pass.

```
[source] NousResearch/hermes-agent
   │ sync-stream-bot (hermes-sync.yml)
01 hermes-upstream      always up-to-date mirror; bots get fixes here
02 hermes-analyser      brand-analysis.py → BRANDING_REPORT.md + OPEN_QUESTIONS.md
03 brand-ideas          branding proposal; owner approves via GitHub Discussions
04 brand-verifier       brand-verifier.py name↔name mapping checks (fails stage on mismatch)
05 dependencies-fixes   dependency fixes (npm/pypi/docker/actions)
06 verify               CI/tests/npm/pypi surface; stops + fill-the-blank if missing
07 semi-stage           ecosystem transforms (npm/docker/config)
08 final                full transform + final verification
09 main (HEAD)          all work lands here
   │ Stage 9
→ PR → nastechai/nastech-agent   (nastech gets ALL fixes)
```

Rules:
- **NEVER** merge from an earlier branch straight into main. Only `final → main`.
- **NEVER** run a later stage before the previous stage's checks pass.
- The pipeline is defined in `.github/workflows/stage-pipeline.yml`. To add
  stages, append a job with `needs: <previous job>` and correct source/target.
- `main` must always stay green; the guard blocks non-`final` PRs into main.

## 3. Branding rules (hermes ecosystem → NasTech)

Branding must convert the hermes ecosystem to NasTech **exactly** as below.
The mapping is enforced by `.github/scripts/brand-verifier.py` in the
`brand-verifier` stage — a wrong mapping FAILS the pipeline.

| Old (hermes ecosystem)   | New (NasTech brand)        | Allowed |
|--------------------------|----------------------------|---------|
| `hermes`                 | `nastech`                  | ✅ verified |
| `hermes-agent`           | `nastech-agent`            | ✅ |
| `hermes_agent`           | `nastech_agent`            | ✅ |
| `nous-research`          | `nastech-research`         | ✅ |
| `nousresearch`           | `nastechresearch`          | ✅ |
| `NousResearch`           | `NasTechResearch`          | ✅ |
| `@nous-research` (npm)   | `@nastech-research` (npm)  | ✅ npm scope must match hermes layout but nastech brand |
| `nousresearchai`         | `nastechairesearch`        | ✅ |

**FORBIDDEN (these MUST fail verification):**
- `hermes` mapped to `nastechai` → ❌ (must be `nastech`)
- `@nous-research` mapped to `@nous` → ❌
- `nastechai-research` → ❌ (must be `nastech-research`)
- `nastechai-researchai` → ❌ (must be `nastechairesearch`)
- ANY leftover `nous*` / `hermes*` token → ❌

Every repo and every file type must be checked: source code, npm manifests,
pyproject/setup, Docker labels, CI YAML, docs, and package scopes.

## 4. Verification focus (what is FATAL vs NOT fatal)

- **FATAL (stage stops):** missing CI workflow, missing tests, missing npm
  manifest / `@nastech-research` scope, missing Python package metadata,
  missing README, branding mismatches, failed tests.
- **NOT FATAL (recorded, does not stop):** checks that fail only because of
  insufficient tokens / quotas (e.g. Docker image pulls/builds hitting rate
  limits). Focus is **tests, CI, npm, pypi**. When a manifest is missing, the
  stage STOPS and posts a fill-the-blank question list to a **GitHub
  Discussion**; the owner answers there.

## 5. Owner approval via GitHub Discussions

- Branding proposals must be approved by the **owner** before `brand-verifier`.
- Approval channel: a GitHub **Discussion** titled with `brand-ideas`.
- Owner approves by **commenting** `yes` (or `approve`), or by **editing** the
  discussion body — both are detected by `brand-discussion-watch.yml`.
- Approval is recorded to `brand-approval.md` on the `brand-ideas` branch.
  Stage 3 refuses to promote until that file exists.
- Answers to fill-the-blank questions are recorded to `brand-answers.md`.
- Only the repo owner's comments/edits count. Bots never self-approve.

## 6. Sync & the sync-stream bot

- `hermes-upstream` is pulled from `NousResearch/hermes-agent` every 4h by
  `hermes-sync.yml`. It is the single source of fixes for all downstream bots.
- `sync-stream-bot.yml` runs every 30 min: checks every pipeline branch for
  new commits, refreshes `INCOMING_REPORT.md`, keeps a tracking issue, and
  sends ONE Telegram notification per batch of new commits.
- **Never** send notifications when nothing changed.

## 7. Notifications (professional, spam-free)

Only meaningful lifecycle events are reported to Telegram:
- New commits on `hermes-upstream` / pipeline branches (batched, with
  `INCOMING_REPORT.md` attached).
- Stage success / failure.
- Pipeline finished → `nastech-agent` PR opened.
- Owner approval recorded.
- Fill-the-blank needs (missing manifests).

No heartbeat, no "still running", no noise. When a token-limited check fails
(Docker etc.) do NOT fail the run or notify as a pipeline failure.

## 8. Bot identity

All automated commits use:
```
name:  NasTech Sync Bot
email: sync@nastechai.dev
```
Automated PRs from the pipeline are titled `chore(...): ... [auto]`.

## 9. AGENTS acting in this repo must

1. Read this file first.
2. Never touch `main` directly unless the promotion is from `final` (Stage 8)
   or a legitimate system config commit on main (workflows/scripts/rules).
3. Keep brand mappings exactly as in section 3.
4. Report problems, never guess brand names — ask through the Discussion flow.
5. When fixing a failed stage, fix it, then let the pipeline promote through
   the ordered stages — do not bypass.
