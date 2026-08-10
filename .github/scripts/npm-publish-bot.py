#!/usr/bin/env python3
"""
npm Publish Bot — publishes the nastech npm packages that are BEHIND their
hermes parity versions. Reads RELEASE_REQUEST.md aliases, compares the npm
registry, locates each package's source inside the nastech-agent checkout,
bumps to the hermes version and publishes (requires NPM_TOKEN).

Usage:
    npm-publish-bot.py --repo . --agent-dir /path/to/nastech-agent \
        [--only nastech-parser] [--dry-run]

Writes PUBLISH_RESULT.md. Exits 0 if all behind packages published, 1 otherwise.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import requests

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s*(.+)$")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")
HEADER_PAIRS = {("hermes package", "nastech package")}


def parse_aliases(text):
    aliases = []
    current = None
    for line in text.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            current = m.group(2).strip().lower()
            continue
        if current and "package" in current and line.strip().startswith("|"):
            m2 = TABLE_ROW_RE.match(line.strip())
            if not m2:
                continue
            cells = [c.strip() for c in m2.groups()]
            if all(re.fullmatch(r"-+", c) for c in cells if c):
                continue
            if len(cells) >= 2 and (cells[0].lower(), cells[1].lower()) in HEADER_PAIRS:
                continue
            if len(cells) >= 2 and cells[0]:
                aliases.append((cells[0], cells[1]))
    return aliases


def semver_key(v):
    v = v.lstrip("v").split("+")[0].split("-")[0]
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def npm_latest(pkg):
    r = requests.get(f"https://registry.npmjs.org/{pkg}", timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    if "error" in data:
        return None
    return data.get("dist-tags", {}).get("latest")


def find_package_dir(agent_root, pkg):
    """Find a directory whose package.json has `name == pkg`."""
    for dirpath, dirnames, filenames in os.walk(agent_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "dist", "build", "__pycache__"}]
        if "package.json" in filenames:
            try:
                data = json.load(open(os.path.join(dirpath, "package.json"), encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            if data.get("name") == pkg:
                return dirpath
    return None


def publish(pkg_dir, version, dry_run):
    env = dict(os.environ)
    env["npm_config_access"] = "public"
    bump = ["npm", "version", version, "--no-git-tag-version", "--allow-same-version"]
    push = ["npm", "publish"]
    if dry_run:
        push.append("--dry-run")
    bump_r = subprocess.run(bump, cwd=pkg_dir, capture_output=True, text=True, env=env)
    if bump_r.returncode != 0:
        return False, f"version bump failed: {bump_r.stderr[-400:]}"
    pub_r = subprocess.run(push, cwd=pkg_dir, capture_output=True, text=True, env=env)
    if pub_r.returncode != 0:
        return False, f"publish failed: {pub_r.stderr[-400:]}"
    return True, pub_r.stdout[-300:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--agent-dir", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    text = open(os.path.join(args.repo, "RELEASE_REQUEST.md"), encoding="utf-8").read()
    aliases = parse_aliases(text)
    results = []
    any_fail = False

    for hermes, nastech in aliases:
        if args.only and nastech != args.only:
            continue
        h_latest = npm_latest(hermes)
        n_latest = npm_latest(nastech)
        if not h_latest:
            results.append((nastech, "skipped", "hermes package not on registry"))
            continue
        if n_latest and semver_key(n_latest) >= semver_key(h_latest):
            results.append((nastech, "ok", f"already at {n_latest} (hermes {h_latest})"))
            continue
        pkg_dir = find_package_dir(args.agent_dir, nastech)
        if not pkg_dir:
            results.append((nastech, "no-source",
                            f"source not found in nastech-agent; publish manually: npm publish {nastech}@{h_latest}"))
            any_fail = True
            continue
        ok, msg = publish(pkg_dir, h_latest, args.dry_run)
        results.append((nastech, "published" if ok else "failed", msg))
        if not ok:
            any_fail = True

    lines = ["# npm Publish Result", ""]
    for pkg, status, msg in results:
        lines.append(f"- `{pkg}` — **{status}**: {msg}")
    report = "\n".join(lines)
    with open("PUBLISH_RESULT.md", "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
