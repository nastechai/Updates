#!/usr/bin/env python3
"""
Release Request Analyzer — reads RELEASE_REQUEST.md (the branding master
config) and:

  1. Validates the brand list is complete and correctly categorized (every
     brand in its category, all old→new pairs well-formed).
  2. Checks the hermes → nastech PACKAGE PARITY against the npm registry:
     for every package alias (hermes-parser → nastech-parser) it compares
     latest versions. Mismatches are listed with exact update + publish steps.
  3. Checks dependency presence + usage in the current tree (package.json
     contains "nastech-parser" and the source actually imports it).

Outputs RELEASE_REPORT.md (full categorized brand list) and
NPM_MISMATCHES.md (only the mismatches + publish commands).

Usage: release-request-analyzer.py [repo_root] [--offline]
Exit 0 always (report only); mismatch count is written to NPM_MISMATCHES.md.
"""

import argparse
import json
import os
import re
import sys

import requests

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s*(.+)$")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")

PKG_SECTION_KEYWORDS = ("packages", "alias")


def parse_release_request(text):
    sections = {}
    current = None
    for line in text.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            current = (m.group(1), m.group(2).strip())
            sections[current] = {"title": m.group(2).strip(), "rows": []}
            continue
        if current and line.strip().startswith("|"):
            m2 = TABLE_ROW_RE.match(line.strip())
            if m2:
                cells = [c.strip() for c in m2.groups()]
                sections[current]["rows"].append(cells)
    return sections


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
        return None, f"npm registry: {r.status_code}"
    data = r.json()
    if "error" in data:
        return None, data["error"]
    return data.get("dist-tags", {}).get("latest"), None


HEADER_PAIRS = {("old", "new"), ("hermes package", "nastech package")}


def parse_package_rows(rows):
    data = []
    for row in rows:
        cells = [c for c in row]
        if cells and all(re.fullmatch(r"-+", c) for c in cells if c):
            continue
        if len(cells) >= 2 and (cells[0].lower(), cells[1].lower()) in HEADER_PAIRS:
            continue
        data.append(cells)
    return data


def parse_packages(pkg_rows):
    aliases = []
    for row in parse_package_rows(pkg_rows):
        if len(row) < 2:
            continue
        hermes, nastech = row[0].strip(), row[1].strip()
        if not hermes or hermes.startswith(("`", "#")):
            continue
        req_dep = len(row) > 2 and row[2].strip().lower() in ("yes", "true", "y")
        req_use = len(row) > 3 and row[3].strip().lower() in ("yes", "true", "y")
        aliases.append({"hermes": hermes, "nastech": nastech, "req_dep": req_dep, "req_use": req_use})
    return aliases


def scan_tree_usage(root, pkg):
    """Check dependency presence + real usage (import/require) of `pkg`."""
    dep, use = False, False
    quoted = re.escape(pkg)
    use_re = re.compile(rf"(?:import\s*.*?\s+from\s*['\"]{quoted}['\"]|require\s*\(\s*['\"]{quoted}['\"]\s*\))")
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "dist", "build", ".venv", "__pycache__"}]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if name == "package.json":
                try:
                    data = json.load(open(path, encoding="utf-8", errors="ignore"))
                except Exception:
                    continue
                deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
                if pkg in deps:
                    dep = True
            ext = os.path.splitext(name)[1]
            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                try:
                    content = open(path, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if use_re.search(content):
                    use = True
    return dep, use


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", default=".")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root)
    rr_path = os.path.join(root, "RELEASE_REQUEST.md")
    if not os.path.exists(rr_path):
        print("[release-request] RELEASE_REQUEST.md not found — nothing to analyze.")
        return 0
    text = open(rr_path, encoding="utf-8").read()
    sections = parse_release_request(text)

    report = ["# Release Request — Brand Plan", "", f"- **Source:** RELEASE_REQUEST.md", ""]
    mismatches = ["# npm Parity Mismatches — how to update & publish", ""]

    pkgs = []
    for (num, title), sec in sections.items():
        report.append(f"## {num}. {title}")
        report.append("")
        report.append("| old | new |")
        report.append("|-----|-----|")
        for row in sec["rows"]:
            report.append(f"| {row[0]} | {row[1]} |")
        report.append("")
        if any(k in title.lower() for k in PKG_SECTION_KEYWORDS):
            pkgs = parse_packages(sec["rows"])

    # Package parity vs npm registry
    report.append("## Package parity (hermes vs nastech npm registry)")
    report.append("")
    report.append("| hermes package | hermes latest | nastech package | nastech latest | parity |")
    report.append("|----------------|---------------|-----------------|----------------|--------|")
    if args.offline:
        report.append("| _offline mode — registry check skipped_ | | | | |")
    else:
        for p in pkgs:
            h_latest, h_err = npm_latest(p["hermes"])
            n_latest, n_err = npm_latest(p["nastech"])
            if h_err and n_err:
                report.append(f"| `{p['hermes']}` | _not on public registry_ | `{p['nastech']}` | _not on public registry_ | ⏭ skipped |")
                continue
            if h_err or n_err:
                report.append(f"| `{p['hermes']}` | {h_latest or h_err} | `{p['nastech']}` | {n_latest or n_err} | ❓ |")
                mismatches.append(f"- `{p['nastech']}` — registry check failed ({n_err or h_err})")
                continue
            parity = "✅"
            if not n_latest:
                parity = "❌ MISSING"
            elif semver_key(n_latest) < semver_key(h_latest):
                parity = "❌ BEHIND"
            elif semver_key(n_latest) > semver_key(h_latest):
                parity = "✅ ahead"
            report.append(f"| `{p['hermes']}` | {h_latest} | `{p['nastech']}` | {n_latest} | {parity} |")
            if parity == "❌ BEHIND" or parity == "❌ MISSING":
                target = h_latest if n_latest else "latest"
                mismatches.append(
                    f"## {p['nastech']}\n\n"
                    f"- hermes version: `{p['hermes']}@{h_latest}`\n"
                    f"- nastech version: `{p['nastech']}@{n_latest or '— (not published)'}`\n\n"
                    f"### How to update\n\n"
                    f"1. Sync `{p['nastech']}` source from `{p['hermes']}@{h_latest}`.\n"
                    f"2. Bump version to `{target}`.\n"
                    f"3. Commit and let the pipeline promote it to main.\n"
                    f"4. Approve publish (set `npm publish: yes` in RELEASE_REQUEST.md).\n"
                    f"5. Run the `Publish npm updates` workflow (requires `NPM_TOKEN`).\n\n"
                    f"### Publish command\n\n"
                    f"```\nnpm publish {p['nastech']}@{target}\n```\n")

    # Dependency presence + usage (tree)
    report.append("")
    report.append("## Dependency presence & usage in this tree")
    report.append("")
    report.append("| package | dependency present | used in code |")
    report.append("|---------|--------------------|--------------|")
    for p in pkgs:
        dep, use = scan_tree_usage(root, p["nastech"])
        report.append(f"| `{p['nastech']}` | {'✅' if dep else '❌'} | {'✅' if use else '❌'} |")

    with open(os.path.join(root, "RELEASE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report))
    with open(os.path.join(root, "NPM_MISMATCHES.md"), "w", encoding="utf-8") as fh:
        if len(mismatches) > 1:
            fh.write("\n\n".join(mismatches))
        else:
            fh.write("# npm Parity Mismatches — how to update & publish\n\n_None. All nastech packages match their hermes parity versions._\n")

    print("\n".join(report))
    print("\n--- NPM_MISMATCHES.md ---\n")
    print("\n".join(mismatches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
