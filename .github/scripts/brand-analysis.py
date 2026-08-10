#!/usr/bin/env python3
"""
Brand Analysis — "how it must be branded" analyser for the hermes-analyser stage.

Scans the upstream tree, detects every old-ecosystem brand token (nous*,
hermes*), and produces BRANDING_REPORT.md describing exactly how the code must
be branded into NasTech, plus OPEN_QUESTIONS.md with fill-the-blank questions
when info is missing (answers come back from the owner via GitHub Discussions).

Usage: brand-analysis.py [repo_root] [--out report_dir]
"""

import argparse
import os
import re
import sys
from collections import Counter

BRAND_PAIRS = [
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

OLD_TOKEN = re.compile(r"(nous[\s_-]*research|nousresearch|hermes[\s_-]*agent|hermes|nous)", re.IGNORECASE)

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".tox", ".pytest_cache", ".next", ".cache"}
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".json", ".yaml",
    ".yml", ".toml", ".xml", ".md", ".txt", ".dockerfile", ".env", ".conf",
    ".ini", ".html", ".css", ".scss", ".vue", ".go", ".rs", ".java", ".rb",
    ".php", ".tf", ".pl", ".c", ".cpp", ".h",
}


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTENSIONS or name.lower() in ("dockerfile", "makefile"):
                yield os.path.join(dirpath, name)


def scan(root):
    hits = Counter()
    files_with_hits = []
    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue
        found = set(OLD_TOKEN.findall(content.lower()))
        if found:
            for t in found:
                hits[t] += 1
            files_with_hits.append((os.path.relpath(path, root), sorted(found)))
    return hits, files_with_hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", default=".")
    ap.add_argument("--out", default=".", help="directory to write BRANDING_REPORT.md / OPEN_QUESTIONS.md")
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root)
    hits, files_with_hits = scan(root)

    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)

    report = [
        "# Branding Report (Hermes Analyser)",
        "",
        f"- **Analysed root:** `{root}`",
        f"- **Old-brand token occurrences:** {sum(hits.values())} across {len(files_with_hits)} files",
        "",
        "## Brand mapping plan",
        "",
        "| Old (hermes ecosystem) | New (NasTech brand) |",
        "|------------------------|---------------------|",
    ]
    for old, new in BRAND_PAIRS:
        report.append(f"| `{old}` | `{new}` |")
    report.append("")
    report.append("## Detected old-brand tokens (to rebrand)")
    report.append("")
    if hits:
        for token, count in hits.most_common():
            report.append(f"- `{token}` — {count} occurrence(s)")
    else:
        report.append("_No old-brand tokens detected._")
    report.append("")

    questions = [
        "# Open Branding Questions (fill the blanks)",
        "",
        "> These are answered by the owner in the **brand-ideas GitHub Discussion**.",
        "> Post a comment (or edit the discussion body) with the answers; the bot reads",
        "> comments **and** edits and records the approval.",
        "",
    ]
    needs = []
    if not os.path.exists(os.path.join(root, "package.json")):
        needs.append("npm manifest is missing — add `package.json` with the `@nastech-research` scope.")
    if not os.path.exists(os.path.join(root, "pyproject.toml")) and not os.path.exists(os.path.join(root, "setup.py")):
        needs.append("Python package metadata is missing — add `pyproject.toml` with the nastech name.")
    if not os.path.exists(os.path.join(root, ".github/workflows/ci.yml")):
        needs.append("CI workflow is missing — add `.github/workflows/ci.yml`.")
    if not os.path.exists(os.path.join(root, "Dockerfile")) and not os.path.exists(os.path.join(root, "docker")):
        needs.append("Container image definition is missing — add `Dockerfile` / `docker/`.")
    if not os.path.exists(os.path.join(root, "README.md")):
        needs.append("README is missing — add `README.md` describing NasTech.")

    if needs:
        for n in needs:
            questions.append(f"- [ ] {n}")
        questions.append("")
        questions.append("Reply to the discussion with: `yes` to approve, or paste answers to the blanks.")
        questions.append("")
    else:
        questions.append("_No missing manifests detected._")
        questions.append("")

    for old, new in BRAND_PAIRS:
        questions.append(f"- Blank: what should replace `{old}` → `{new}` ? (default: `{new}`)")

    with open(os.path.join(outdir, "BRANDING_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report))
    with open(os.path.join(outdir, "OPEN_QUESTIONS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(questions))

    print("\n".join(report))
    print("\n--- OPEN_QUESTIONS.md ---\n")
    print("\n".join(questions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
