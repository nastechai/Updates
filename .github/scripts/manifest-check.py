#!/usr/bin/env python3
"""
Manifest Check — verifies the essential CI/test/npm/pypi surface exists for a
branch before it is allowed to promote. If something is missing the stage
STOPS and emits MANIFEST_NEEDS.md (the fill-the-blank list) which is posted to
a GitHub Discussion for the owner to answer.

Focus set (per the owner): CI, tests, npm, pypi. Token-limited things like
Docker builds are intentionally NOT required here.

Usage: manifest-check.py [repo_root] [--out manifest_dir]
Exit 0 = complete, 1 = missing items.
"""

import argparse
import os
import sys

REQUIRED = [
    ("npm", "package.json", "npm manifest (`package.json`)"),
    ("npm-scope", "package.json:@nastech-research", "npm scope `@nastech-research` in package.json"),
    ("pypi", "pyproject.toml|setup.py|setup.cfg", "Python package metadata (pyproject.toml / setup.py)"),
    ("ci", ".github/workflows/ci.yml", "CI workflow (`.github/workflows/ci.yml`)"),
    ("tests", "tests/", "tests directory (`tests/`)"),
    ("docs", "README.md", "README.md"),
]


def check(root):
    missing = []
    for key, spec, label in REQUIRED:
        present = False
        for candidate in spec.split("|"):
            if key == "npm-scope":
                p = os.path.join(root, "package.json")
                if os.path.exists(p):
                    try:
                        content = open(p, encoding="utf-8", errors="ignore").read()
                        if "@nastech-research" in content:
                            present = True
                    except Exception:
                        pass
            else:
                p = os.path.join(root, candidate)
                if os.path.exists(p):
                    present = True
                    break
        if not present:
            missing.append(label)
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", default=".")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root)
    missing = check(root)
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)

    with open(os.path.join(outdir, "MANIFEST_NEEDS.md"), "w", encoding="utf-8") as fh:
        fh.write("# Manifest Needs (fill the blanks)\n\n")
        if missing:
            fh.write("The following items are missing and must be provided by the owner:\n\n")
            for i, m in enumerate(missing, start=1):
                fh.write(f"{i}. [ ] {m}\n")
            fh.write("\nReply in the discussion with answers or `yes` to approve.\n")
        else:
            fh.write("_All required manifests present._\n")

    if missing:
        print("[MANIFEST-CHECK] FAIL — missing:", " | ".join(missing), file=sys.stderr)
        for m in missing:
            print("-", m)
        return 1
    print("[MANIFEST-CHECK] PASS — CI/tests/npm/pypi surface complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
