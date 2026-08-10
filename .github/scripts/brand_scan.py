#!/usr/bin/env python3
"""
BrandGuard CI scanner.

Scans the diff between BASE_SHA and the current checkout for any write that
would rename/rebrand/drop an existing dependency. Fails the build if found.

Usage:
  python3 brand_scan.py BASE_SHA [HEAD_SHA]

Runs in CI (security-scan.yml) and locally:
  git fetch origin main --depth=1 && python3 .github/scripts/brand_scan.py origin/main

Exits 0 when the diff is brand-safe, 1 when a violation is found.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from llm_client import load_config  # noqa: E402
from security_guard import BrandGuard, SecurityError  # noqa: E402


def git(args, cwd=".") -> str:
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60)
    return p.stdout or ""


def changed_files(base: str, head: str, cwd=".") -> list:
    if head == "HEAD":
        out = git(["diff", base, "--name-only", "--"], cwd=cwd)
    else:
        out = git(["diff", f"{base}...{head}", "--name-only", "--"], cwd=cwd)
    return [f for f in out.strip().splitlines() if f.strip()]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: brand_scan.py BASE_SHA [HEAD_SHA]", file=sys.stderr)
        return 2
    base = sys.argv[1]
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    root = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()

    cfg = load_config()
    bg = BrandGuard(cfg)
    files = changed_files(base, head, cwd=root)
    violations = []

    for rel_path in files:
        if not BrandGuard.is_manifest(rel_path) and not bg._guard_file(rel_path):
            continue
        old = git(["show", f"{base}:{rel_path}"], cwd=root)
        new = ""
        try:
            with open(os.path.join(root, rel_path), "r", encoding="utf-8", errors="ignore") as f:
                new = f.read()
        except OSError:
            continue
        try:
            bg.check_content(rel_path, old, new)
        except SecurityError as e:
            violations.append(str(e))

    if violations:
        print("BrandGuard scan FAILED:")
        for v in violations:
            print("  -", v)
        return 1
    print(f"BrandGuard scan OK ({len(files)} changed files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
