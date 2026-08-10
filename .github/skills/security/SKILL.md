---
name: security
description: Cross-cutting security review applied alongside every other skill.
when: "always loaded with every review"
---

# Security Review Skill

Apply this skill in ADDITION to the primary language skill on every file.

## What to check (any language)
- **Secrets & credentials**: hardcoded API keys, tokens, passwords, private keys, `.env` committed, connection strings with embedded passwords, `id_rsa`/`.pem`/`.key` files, cloud provider keys (`AKIA...`, `sk-...`, `xoxb-...`, `ghp_...`, `AIza...`).
- **Injection**: SQL/command/code injection, unsafe deserialization, template injection, path traversal, SSRF (URLs built from user input).
- **AuthN/AuthZ**: missing auth checks on new endpoints, auth bypass, insecure token validation (accepts any token, no expiry check), privilege escalation, cross-tenant data access (missing ownership scoping).
- **Data handling**: logging secrets/PII, storing passwords in plaintext, weak hashing (MD5/SHA1 for passwords), predictable session IDs.
- **Crypto**: homegrown crypto, `ECB` mode, fixed IVs, weak randomness for security tokens.

## What NOT to flag
- Theoretical issues with no reachable path (no attacker-controlled input reaches the code).
- Standard library usage that is fine in context.

## Severity guidance
- **critical**: any directly exploitable vuln or committed credential — ALWAYS request changes.
- **major**: weakness with an attack path but requiring conditions.
- **minor**: hardening / best-practice with no immediate exploit.

## Output
Findings with path, line, severity, category ("security"), confidence, message, suggestion. Never propose logging the credential to debug it.
