# Release Request — NasTech Branding Master Config

> Edit this file to tell the pipeline **how branding must be done**. When you
> update it, the pipeline re-reads it and understands the full brand plan:
> every brand, in its category, plus the hermes → nastech package parity.
> If hermes and nastech npm packages do not match, the pipeline opens a
> Discussion telling you how to update and publish them.
>
> To publish npm updates: set `npm publish: yes` below and provide an
> `NPM_TOKEN` repo secret, then run the `Publish npm updates` workflow.

## Approval
- [ ] Brand plan approved (owner comments `yes` in the brand-ideas Discussion)
- [ ] npm publish approved (`npm publish: yes`)

## 1. Product
| old | new |
|-----|-----|
| hermes-agent | nastech-agent |
| hermes | nastech |
| hermes_agent | nastech_agent |

## 2. Organization / GitHub
| old | new |
|-----|-----|
| nous | nastech |
| nous-research | nastech-research |
| nous_research | nastech_research |
| nousresearch | nastechresearch |
| NousResearch | NasTechResearch |
| NOUS_RESEARCH | NASTECH_RESEARCH |
| nousresearchai | nastechairesearch |
| nous-researchai | nastechairesearch |

## 3. npm scope
| old | new |
|-----|-----|
| @nous-research | @nastech-research |

## 4. Docker org
| old | new |
|-----|-----|
| nousresearch | nastechairesearch |
| nous-research | nastech-research |

## 5. Domains
| old | new |
|-----|-----|
| nous-research.com | nastech-research.com |
| nousresearch.com | nastechresearch.com |
| nousresearchai.com | nastechairesearch.com |

## 6. Packages (aliases) — hermes → nastech parity
| hermes package | nastech package | require dependency | require used |
|----------------|-----------------|--------------------|--------------|
| hermes-parser | nastech-parser | yes | yes |
| hermes-agent | nastech-agent | yes | yes |
| hermes-eslint | nastech-eslint | yes | yes |
| @hermes-parser/babel-plugin | @nastech-parser/babel-plugin | yes | yes |
| @hermes-parser/test-utils | @nastech-parser/test-utils | no | no |
| hermes-transform | nastech-transform | no | no |

## 7. npm parity check (auto)
> The analyzer compares the npm registry versions of every hermes vs nastech
> package above. Mismatches are posted to a Discussion with exact update +
> publish commands, e.g.:
>
>     nastech-parser@0.25.1  (hermes-parser@0.37.0)  →  bump to 0.37.0
>     npm publish nastech-parser@0.37.0
