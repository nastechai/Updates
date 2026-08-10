#!/usr/bin/env python3
"""
Brand Verifier — name-to-name brand mapping verification.

Two modes:
  --mode mapping  (default, Stage 4): verifies the BRANDING MAPPING DATABASE is
                  complete and correct. Confirms the hermes→nastech translation
                  table and flags FORBIDDEN combos (hermes→nastechai,
                  @nous-research→@nous, nastechai-research, nastechai-researchai,
                  any leftover nous*/hermes* mapping entries).
  --mode tree     (Stage 8): verifies the actual SOURCE TREE is fully branded —
                  no leftover old-brand tokens in real product code. The
                  automation control dir (.github/), test fixtures, and docs
                  intentionally reference the upstream and are excluded.

The mapping MUST match the hermes ecosystem layout with the nastech brand:
    hermes          -> nastech
    hermes-agent    -> nastech-agent
    hermes_agent    -> nastech_agent
    nous            -> nastech
    nous-research   -> nastech-research
    nous_research   -> nastech_research
    nousresearch    -> nastechresearch
    NousResearch    -> NasTechResearch
    @nous-research  -> @nastech-research   (npm scope)
    nousresearchai  -> nastechairesearch
    nous-researchai -> nastechairesearch

Usage: brand-verifier.py [repo_root] [--mode mapping|tree] [--report out.md]
Exit code 0 = pass, 1 = fail.
"""

import argparse
import os
import re
import sys

ALLOWED_PAIRS = [
    ("hermes-agent", "nastech-agent"),
    ("hermes_agent", "nastech_agent"),
    ("hermes", "nastech"),
    ("nous-research", "nastech-research"),
    ("nous_research", "nastech_research"),
    ("nousresearch", "nastechresearch"),
    ("NousResearch", "NasTechResearch"),
    ("NOUS_RESEARCH", "NASTECH_RESEARCH"),
    ("@nous-research", "@nastech-research"),
    ("nousresearchai", "nastechairesearch"),
    ("nous-researchai", "nastechairesearch"),
]

# Forbidden *with* a separator only — `nastechairesearch` (no separator) is the
# CORRECT org name, while `nastechai-research` / `nastechai_research` are wrong.
FORBIDDEN_MAPPINGS = [
    (re.compile(r"nastechai[\s_-]*researchai", re.IGNORECASE), "nastechai-researchai (must be nastechairesearch)"),
    (re.compile(r"nastechai[-_]\s*research\b", re.IGNORECASE), "nastechai-research (must be nastech-research)"),
    (re.compile(r"@nous(?![-_])"), "@nous (npm scope must be @nastech-research)"),
    (re.compile(r"@nous-research\b", re.IGNORECASE), "@nous-research (must be @nastech-research)"),
    (re.compile(r"\bhermes-agent\b", re.IGNORECASE), "hermes-agent (must be nastech-agent)"),
    (re.compile(r"\bhermes_agent\b", re.IGNORECASE), "hermes_agent (must be nastech_agent)"),
    (re.compile(r"\bnous-research\b", re.IGNORECASE), "nous-research (must be nastech-research)"),
    (re.compile(r"\bnousresearch\b", re.IGNORECASE), "nousresearch (must be nastechresearch)"),
    (re.compile(r"\bhermes\b", re.IGNORECASE), "hermes (must be nastech)"),
]

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".json", ".yaml",
    ".yml", ".toml", ".xml", ".md", ".txt", ".dockerfile", ".env", ".conf",
    ".ini", ".html", ".css", ".scss", ".vue", ".go", ".rs", ".java", ".rb",
    ".php", ".tf", ".pl", ".c", ".cpp", ".h",
}
# Automation control + fixtures intentionally reference the upstream.
TREE_SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv",
                  "__pycache__", ".tox", ".pytest_cache", ".next", ".cache",
                  ".github", "tests", "docs", "contributors", "scripts"}
# Files that legitimately talk about the upstream name (control/notes).
TREE_SKIP_FILES = {"INCOMING_REPORT.md", "VERIFICATION_REPORT.json",
                   "SYSTEM_INVENTORY.md", "BRANDING_REPORT.md",
                   "BRAND_VERIFICATION.md", "OPEN_QUESTIONS.md",
                   "MANIFEST_NEEDS.md", "STAGE_REPORT.md", "FAILURE_REPORT.md",
                   "AGENTS.md"}


def iter_text_files(root, skip_dirs):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTENSIONS or name.lower() in ("dockerfile", "makefile"):
                yield os.path.join(dirpath, name)


def mode_mapping(root):
    """Verify the mapping table itself: every NEW name must be pure NasTech
    (never contain an old-brand token or a forbidden combination)."""
    failures = []
    old_tokens = [re.compile(r"nous", re.IGNORECASE), re.compile(r"hermes", re.IGNORECASE)]
    for old, new in ALLOWED_PAIRS:
        if any(t.search(new) for t in old_tokens):
            failures.append((f"mapping {old} → {new}",
                             f"new name '{new}' still contains an old-brand token"))
        for pat, why in FORBIDDEN_MAPPINGS:
            if pat.search(new):
                failures.append((f"mapping {old} → {new}", why))
    return failures


def mode_tree(root):
    failures = []
    for path in iter_text_files(root, TREE_SKIP_DIRS):
        base = os.path.basename(path)
        if base in TREE_SKIP_FILES:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, start=1):
            for pat, why in FORBIDDEN_MAPPINGS:
                if pat.search(line):
                    rel = os.path.relpath(path, root)
                    failures.append((f"{rel}:{lineno}", f"{why} :: {line.strip()[:120]}"))
                    break
    # npm scope check
    for path in iter_text_files(root, TREE_SKIP_DIRS):
        if os.path.basename(path).lower() in ("package.json", "package-lock.json",
                                              "pnpm-lock.yaml", "yarn.lock",
                                              "npm-shrinkwrap.json", "pyproject.toml"):
            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in re.finditer(r"@nous[-_a-z]*", content):
                failures.append((os.path.relpath(path, root), f"npm scope {m.group(0)} (must be @nastech-research)"))
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", default=".")
    ap.add_argument("--mode", default="mapping", choices=["mapping", "tree"])
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root)
    failures = mode_mapping(root) if args.mode == "mapping" else mode_tree(root)

    lines_out = [
        "# Brand Verification Report",
        "",
        f"- **Mode:** {args.mode}",
        f"- **Repo root:** `{root}`",
        f"- **Result:** {'PASS' if not failures else 'FAIL'}",
        "",
        "## Allowed mappings (must hold)",
        "",
    ]
    for old, new in ALLOWED_PAIRS:
        lines_out.append(f"- `{old}` → `{new}`")
    lines_out.append("")
    lines_out.append("## Failures")
    lines_out.append("")
    if failures:
        seen = set()
        for loc, why in failures:
            key = (loc, why)
            if key in seen:
                continue
            seen.add(key)
            lines_out.append(f"- **{loc}** — {why}")
    else:
        lines_out.append("_None. Branding matches NasTech._")
    lines_out.append("")

    report = "\n".join(lines_out)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report)

    print(report)
    if failures:
        print(f"\n[BRAND-VERIFIER:{args.mode}] FAIL — {len(failures)} issue(s)", file=sys.stderr)
        return 1
    print(f"\n[BRAND-VERIFIER:{args.mode}] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
