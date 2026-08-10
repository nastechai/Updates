# NasTech Branding Pipeline Report - full
**Timestamp**: 2026-08-10 02:44:25
**Status**: ✅ SUCCESS

## Stage Details
This report documents the results of the **full** stage in the branding transformation pipeline.

## Execution Summary
### Log: orchestrator.log
```text
[0;34m[•][0m NasTech Pipeline Orchestrator v4.0
[0;34m[•][0m Target Stage: full
[0;34m[•][0m Logs Directory: /tmp/nastech-logs-20260810-024418

[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;36m[1m  STAGE: VERIFY[0m
[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;34m[•][0m Running initial validation on raw sync...
[0;32m[✓][0m Verification stage complete. Results in verify.log

[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;36m[1m  STAGE: SEMI-STAGE[0m
[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;34m[•][0m Applying ecosystem-specific transformations (npm, Docker, Config)...
[0;32m[✓][0m Semi-Stage transformation complete.

[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;36m[1m  STAGE: FINAL[0m
[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;34m[•][0m Running full ecosystem transformation and final verification...
[0;34m[•][0m Renaming files and directories...
[0;32m[✓][0m Final stage complete.

[0;36m[1m════════════════════════════════════════════════════════════════[0m
[0;36m[1m  GENERATING REPORT[0m
[0;36m[1m════════════════════════════════════════════════════════════════[0m

```

### Log: verify.log
```text
[91m[✗][0m ✗ Validation failed

[96m============================================================[0m
[96m[1m  Branding Validation[0m
[96m============================================================[0m
✗ hermes_references: 8335 violation(s)
✗ nous_references: 3 violation(s)
✗ docker_references: 3 violation(s)
✗ filenames: 90 violation(s)
✗ directories: 11 violation(s)
✗ npm_packages: 9 violation(s)

```

### Log: npm.log
```text

[96m============================================================[0m
[96m[1m  npm Branding Validation[0m
[96m============================================================[0m
[92m[✓][0m Violations found: 21
[92m[✓][0m Transformations applied: 12

Violations:
  - ./apps/bootstrap-installer/package.json: Package name contains 'hermes': @hermes/bootstrap-installer
  - ./apps/bootstrap-installer/package.json: Dependency uses @nous-research scope: @nous-research/ui
  - ./apps/desktop/package.json: Package name contains 'hermes': hermes
  - ./apps/desktop/package.json: Dependency uses @nous-research scope: @nous-research/ui
  - ./apps/shared/package.json: Package name contains 'hermes': @hermes/shared
  - ./package.json: Package name contains 'hermes': hermes-agent
  - ./plugins/platforms/photon/sidecar/package.json: Package name contains 'hermes': @hermes-agent/photon-sidecar
  - ./scripts/whatsapp-bridge/package.json: Package name contains 'hermes': hermes-whatsapp-bridge
  - ./tests-js/package.json: Package name contains 'hermes': @hermes/root-tests
  - ./ui-tui/package.json: Package name contains 'hermes': hermes-tui
  - ./ui-tui/packages/hermes-ink/package.json: Package name contains 'hermes': @hermes/ink
  - ./web/package.json: Dependency uses @nous-research scope: @nous-research/ui
  - ./package-lock.json: Locked package name contains 'hermes': hermes-agent
  - ./package-lock.json: Locked package name contains 'hermes': @hermes/bootstrap-installer
  - ./package-lock.json: Locked package name contains 'hermes': hermes
  - ./package-lock.json: Locked package name contains 'hermes': @hermes/shared
  - ./package-lock.json: Locked package name contains 'hermes': @hermes/root-tests
  - ./package-lock.json: Locked package name contains 'hermes': hermes-tui
  - ./package-lock.json: Locked package name contains 'hermes': @hermes/ink
  - ./plugins/platforms/photon/sidecar/package-lock.json: Locked package name contains 'hermes': @hermes-agent/photon-sidecar
  - ./scripts/whatsapp-bridge/package-lock.json: Locked package name contains 'hermes': hermes-whatsapp-bridge

Transformations:
  - ./apps/bootstrap-installer/package.json: 2 replacement(s)
  - ./apps/desktop/package.json: 24 replacement(s)
  - ./apps/shared/package.json: 1 replacement(s)
  - ./package.json: 7 replacement(s)
  - ./plugins/platforms/photon/sidecar/package.json: 2 replacement(s)
  - ./scripts/whatsapp-bridge/package.json: 2 replacement(s)
  - ./tests-js/package.json: 1 replacement(s)
  - ./ui-tui/package.json: 4 replacement(s)
  - ./ui-tui/packages/hermes-ink/package.json: 1 replacement(s)
  - ./package-lock.json: 15 replacement(s)
  - ./plugins/platforms/photon/sidecar/package-lock.json: 2 replacement(s)
  - ./scripts/whatsapp-bridge/package-lock.json: 2 replacement(s)
[91m[✗][0m ✗ npm branding validation failed

```

### Log: docker.log
```text

[0;36m════════════════════════════════════════[0m
[0;36m  Docker Branding Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Repository: .
[0;34m[•][0m Fix mode: true

[0;36m════════════════════════════════════════[0m
[0;36m  Dockerfile Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Checking: ./Dockerfile
[1;33m[⚠][0m   Found HERMES_ environment variables
[0;32m[✓][0m   Fixed environment variables
[1;33m[⚠][0m   Found /opt/hermes path references
[0;32m[✓][0m   Fixed path references

[0;36m════════════════════════════════════════[0m
[0;36m  Docker Compose Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Checking: ./docker-compose.windows.yml
[1;33m[⚠][0m   Found nousresearch/hermes image references
[0;32m[✓][0m   Fixed image references
[1;33m[⚠][0m   Found HERMES_ environment variables
[0;32m[✓][0m   Fixed environment variables
[0;34m[•][0m Checking: ./docker-compose.yml
[1;33m[⚠][0m   Found HERMES_ environment variables
[0;32m[✓][0m   Fixed environment variables
[0;34m[•][0m Checking: ./tests/e2e/matrix_xsign_bootstrap/docker-compose.yml

[0;36m════════════════════════════════════════[0m
[0;36m  GitHub Actions Workflow Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Checking: ./.github/workflows/ci-review-comment.yml
[0;34m[•][0m Checking: ./.github/workflows/issue-tracker.yml
[0;34m[•][0m Checking: ./.github/workflows/stage-1-sync-verify.yml
[0;34m[•][0m Checking: ./.github/workflows/stage-2-semi-stage.yml
[0;34m[•][0m Checking: ./.github/workflows/stage-3-final.yml
[0;34m[•][0m Checking: ./.github/workflows/stage-4-production-pr.yml
[0;34m[•][0m Checking: ./.github/workflows/ci.yml
[0;34m[•][0m Checking: ./.github/workflows/contributor-check.yml
[0;34m[•][0m Checking: ./.github/workflows/deploy-site.yml
[0;34m[•][0m Checking: ./.github/workflows/docker-lint.yml
[0;34m[•][0m Checking: ./.github/workflows/docker.yml
[1;33m[⚠][0m   Found nousresearch/hermes Docker references
[0;32m[✓][0m   Fixed Docker references
[0;34m[•][0m Checking: ./.github/workflows/docs-site-checks.yml
[0;34m[•][0m Checking: ./.github/workflows/e2e-desktop.yml
[0;34m[•][0m Checking: ./.github/workflows/history-check.yml
[0;34m[•][0m Checking: ./.github/workflows/infographic-check.yml
[0;34m[•][0m Checking: ./.github/workflows/install-e2e-run.yml
[0;34m[•][0m Checking: ./.github/workflows/install-e2e.yml
[0;34m[•][0m Checking: ./.github/workflows/installer-tests.yml
[0;34m[•][0m Checking: ./.github/workflows/js-autofix.yml
[0;34m[•][0m Checking: ./.github/workflows/js-tests.yml
[0;34m[•][0m Checking: ./.github/workflows/label-rerun.yml
[0;34m[•][0m Checking: ./.github/workflows/lint.yml
[0;34m[•][0m Checking: ./.github/workflows/lockfile-diff.yml
[0;34m[•][0m Checking: ./.github/workflows/osv-scanner.yml
[0;34m[•][0m Checking: ./.github/workflows/publish-e2e-evidence.yml
[0;34m[•][0m Checking: ./.github/workflows/review-labels.yml
[0;34m[•][0m Checking: ./.github/workflows/skills-index-freshness.yml
[0;34m[•][0m Checking: ./.github/workflows/skills-index.yml
[0;34m[•][0m Checking: ./.github/workflows/supply-chain-audit.yml
[0;34m[•][0m Checking: ./.github/workflows/tests-os.yml
[0;34m[•][0m Checking: ./.github/workflows/tests.yml
[0;34m[•][0m Checking: ./.github/workflows/uv-lockfile-check.yml

[0;36m════════════════════════════════════════[0m
[0;36m  .dockerignore Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Checking: ./.dockerignore
[1;33m[⚠][0m   Found hermes-related patterns
[0;32m[✓][0m   Fixed patterns

[0;36m════════════════════════════════════════[0m
[0;36m  Registry Configuration Validation[0m
[0;36m════════════════════════════════════════[0m

[0;36m════════════════════════════════════════[0m
[0;36m  Build Script Validation[0m
[0;36m════════════════════════════════════════[0m
[0;34m[•][0m Checking: ./native/fts5_cjk/build.sh
[0;34m[•][0m Checking: ./skills/research/research-paper-writing/templates/neurips2025/Makefile

[0;36m════════════════════════════════════════[0m
[0;36m  Docker Branding Validation Report[0m
[0;36m════════════════════════════════════════[0m
Violations found  : 7
Transformations   : 7
[0;31m[✗][0m ✗ Docker branding validation failed with 7 violation(s)

```

### Log: config.log
```text
[93m[⚠][0m   docker-compose.windows.yml: 6 violation(s)
[93m[⚠][0m   docker-compose.yml: 19 violation(s)
[93m[⚠][0m   .github/dependabot.yml: 2 violation(s)
[93m[⚠][0m   .github/workflows/stage-1-sync-verify.yml: 6 violation(s)
[93m[⚠][0m   .github/workflows/stage-4-production-pr.yml: 1 violation(s)
[93m[⚠][0m   .github/workflows/ci.yml: 1 violation(s)
[93m[⚠][0m   .github/workflows/deploy-site.yml: 9 violation(s)
[93m[⚠][0m   .github/workflows/docker.yml: 15 violation(s)
[93m[⚠][0m   .github/workflows/e2e-desktop.yml: 1 violation(s)
[93m[⚠][0m   .github/workflows/install-e2e-run.yml: 3 violation(s)
[93m[⚠][0m   .github/workflows/install-e2e.yml: 2 violation(s)
[93m[⚠][0m   .github/workflows/skills-index-freshness.yml: 6 violation(s)
[93m[⚠][0m   .github/workflows/skills-index.yml: 3 violation(s)
[93m[⚠][0m   .github/workflows/supply-chain-audit.yml: 1 violation(s)
[93m[⚠][0m   .github/workflows/tests.yml: 2 violation(s)
[93m[⚠][0m   .github/ISSUE_TEMPLATE/bug_report.yml: 15 violation(s)
[93m[⚠][0m   .github/ISSUE_TEMPLATE/config.yml: 10 violation(s)
[93m[⚠][0m   .github/ISSUE_TEMPLATE/feature_request.yml: 11 violation(s)
[93m[⚠][0m   .github/ISSUE_TEMPLATE/setup_help.yml: 21 violation(s)
[93m[⚠][0m   .github/actions/nix-setup/action.yml: 2 violation(s)
[93m[⚠][0m   .hadolint.yaml: 4 violation(s)
[93m[⚠][0m   datagen-config-examples/web_research.yaml: 3 violation(s)
[93m[⚠][0m   locales/af.yaml: 17 violation(s)
[93m[⚠][0m   locales/ar.yaml: 17 violation(s)
[93m[⚠][0m   locales/de.yaml: 17 violation(s)
[93m[⚠][0m   locales/en.yaml: 17 violation(s)
[93m[⚠][0m   locales/es.yaml: 17 violation(s)
[93m[⚠][0m   locales/fr.yaml: 17 violation(s)
[93m[⚠][0m   locales/ga.yaml: 17 violation(s)
[93m[⚠][0m   locales/hu.yaml: 17 violation(s)
[93m[⚠][0m   locales/it.yaml: 17 violation(s)
[93m[⚠][0m   locales/ja.yaml: 17 violation(s)
[93m[⚠][0m   locales/ko.yaml: 17 violation(s)
[93m[⚠][0m   locales/pt.yaml: 17 violation(s)
[93m[⚠][0m   locales/ru.yaml: 17 violation(s)
[93m[⚠][0m   locales/tr.yaml: 17 violation(s)
[93m[⚠][0m   locales/uk.yaml: 17 violation(s)
[93m[⚠][0m   locales/zh-hant.yaml: 17 violation(s)
[93m[⚠][0m   locales/zh.yaml: 17 violation(s)
[93m[⚠][0m   optional-mcps/blender/manifest.yaml: 9 violation(s)
[93m[⚠][0m   optional-mcps/comfy-cloud/manifest.yaml: 8 violation(s)
[93m[⚠][0m   optional-mcps/figma/manifest.yaml: 6 violation(s)
[93m[⚠][0m   optional-mcps/linear/manifest.yaml: 4 violation(s)
[93m[⚠][0m   optional-mcps/n8n/manifest.yaml: 11 violation(s)
[93m[⚠][0m   optional-mcps/unreal-engine/manifest.yaml: 5 violation(s)
[93m[⚠][0m   plugins/disk-cleanup/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/google_meet/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/security-guidance/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/spotify/plugin.yaml: 4 violation(s)
[93m[⚠][0m   plugins/teams_pipeline/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/browser/browser_use/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/browser/browserbase/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/browser/firecrawl/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/cron_providers/chronos/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/dashboard_auth/basic/plugin.yaml: 3 violation(s)
[93m[⚠][0m   plugins/dashboard_auth/drain/plugin.yaml: 3 violation(s)
[93m[⚠][0m   plugins/dashboard_auth/nous/plugin.yaml: 5 violation(s)
[93m[⚠][0m   plugins/dashboard_auth/self_hosted/plugin.yaml: 5 violation(s)
[93m[⚠][0m   plugins/image_gen/fal/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/image_gen/krea/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/image_gen/openai-codex/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/image_gen/openai/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/image_gen/openrouter/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/model-providers/ai-gateway/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/alibaba-coding-plan/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/alibaba/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/anthropic/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/arcee/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/azure-foundry/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/bedrock/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/copilot-acp/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/copilot/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/custom/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/deepseek/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/fireworks/plugin.yaml: 2 violation(s)
[93m[⚠][0m   plugins/model-providers/gemini/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/model-providers/gmi/plugin.yaml: 1 violation(s)
[93m[⚠][0m   plugins/m
... (truncated)
```

### Log: ecosystem.log
```text
[93m[⚠][0m   setup.py: 13 violation(s)
[93m[⚠][0m   Dockerfile: 47 violation(s)
[93m[⚠][0m   .envrc: 4 violation(s)
[93m[⚠][0m   gateway/config.py: 25 violation(s)
[93m[⚠][0m   hermes_cli/config.py: 347 violation(s)
[93m[⚠][0m   hermes_cli/subcommands/config.py: 4 violation(s)
[93m[⚠][0m   optional-skills/security/unbroker/scripts/config.py: 4 violation(s)

[96m======================================================================[0m
[96m[1m  Ecosystem Branding Validation (40+ Ecosystems)[0m
[96m======================================================================[0m
[94m[•][0m Repository: .
[94m[•][0m Fix mode: True

[96m======================================================================[0m
[96m[1m  PYTHON Ecosystem[0m
[96m======================================================================[0m
[92m[✓][0m     Fixed: 10 replacement(s)
[92m[✓][0m   pyproject.toml
[92m[✓][0m   optional-skills/finance/dcf-model/requirements.txt

[96m======================================================================[0m
[96m[1m  NODEJS Ecosystem[0m
[96m======================================================================[0m
[92m[✓][0m   package.json
[92m[✓][0m   package-lock.json
[92m[✓][0m   .npmrc

[96m======================================================================[0m
[96m[1m  GO Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  RUST Ecosystem[0m
[96m======================================================================[0m
[92m[✓][0m   apps/bootstrap-installer/src-tauri/Cargo.toml

[96m======================================================================[0m
[96m[1m  JAVA Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  RUBY Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  PHP Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  DOTNET Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  SCALA Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  CLOJURE Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  ELIXIR Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  HASKELL Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  R Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  PERL Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  SWIFT Ecosystem[0m
[96m======================================================================[0m

[96m======================================================================[0m
[96m[1m  BUILD Ecosystem[0m
[96m======================================================================[0m
[92m[✓][0m   skills/research/research-paper-writing/templates/neurips2025/Makefile

[96m======================================================================[0m
[96m[1m  CICD Ecosystem[0m
[96m======================================================================[0m
[92m[✓][0m   .github/workflows/ci-review-comment.yml
[92m[✓][0m   .github/workflows/issue-tracker.yml
[92m[✓][0m   .github/workflows/stage-1-sync-verify.yml
[92m[✓][0m   .github/workflows/stage-2-semi-stage.yml
[92m[✓][0m   .github/workflows/stage-3-final.yml
[92m[✓][0m   .github/workflows/stage-4-production-pr.yml
[92m[✓][0m   .github/workflows/ci.yml
[92m[✓][0m   .github/workflows/contributor-check.yml
[92m[✓][0m   .github/workflows/deploy-site.yml
[92m[✓][0m   .github/workflows/docker-lint.yml
[92m[✓][0m   .github/workflows/docker.yml
[92m[✓][0m   .github/workflows/docs-site-checks.yml
[92m[✓][0m   .github/workflows/e2e-desktop.yml
[92m[✓][0m   .github/workflows/history-check.yml
[92
... (truncated)
```

### Log: engine.log
```text

[96m============================================================[0m
[96m[1m  Branding Transformation[0m
[96m============================================================[0m
[94m[•][0m Repository: /home/ubuntu/Updates
[94m[•][0m Dry run: False
[92m[✓][0m Files processed: 8600
[92m[✓][0m Files modified: 3775
[92m[✓][0m Total replacements: 52663

[96m============================================================[0m
[96m[1m  File/Directory Renaming[0m
[96m============================================================[0m
[92m[✓][0m Items renamed: 101
[92m[✓][0m ✓ Transformation complete

```

### Log: final_validation.log
```text
[91m[✗][0m ✗ Validation failed

[96m============================================================[0m
[96m[1m  Branding Validation[0m
[96m============================================================[0m
✗ nastech_references: 8423 violation(s)
✓ nous_references: 0 violation(s)
✗ docker_references: 3 violation(s)
✗ filenames: 90 violation(s)
✗ directories: 11 violation(s)
✗ npm_packages: 9 violation(s)

```

---
_Generated by NasTech Pipeline Orchestrator_