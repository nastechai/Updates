#!/usr/bin/env python3
"""
Incoming Report — the sync-stream bot's commit watcher helper.

Given the previous commit and the new commit of a branch, produces a
professional INCOMING_REPORT.md listing every incoming commit (sha, author,
date, subject) so the pipeline and the owner always know what is arriving.

Usage:
    incoming_report.py --repo . --from-ref SHA1 --to-ref SHA2 \
        --branch hermes-upstream [--issue-title "..."]

Exits 0. Writes INCOMING_REPORT.md in the current directory.
"""

import argparse
import os
import subprocess
import sys


def git(*args):
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=os.getcwd(),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--from-ref", required=True, help="old sha/tag")
    ap.add_argument("--to-ref", required=True, help="new sha/tag")
    ap.add_argument("--branch", required=True)
    args = ap.parse_args()

    os.chdir(args.repo)

    if args.from_ref == args.to_ref:
        print("No new commits.")
        open("INCOMING_REPORT.md", "w").write("# Incoming Report\n\n_No new commits._\n")
        return 0

    r = git("log", "--pretty=format:%h|%an|%ad|%s", "--date=short",
            f"{args.from_ref}..{args.to_ref}")
    commits = [line.split("|", 3) for line in r.stdout.strip().splitlines() if line]

    lines = [
        "# Incoming Report",
        "",
        f"- **Branch:** `{args.branch}`",
        f"- **From:** `{args.from_ref}`",
        f"- **To:** `{args.to_ref}`",
        f"- **Incoming commits:** {len(commits)}",
        "",
        "| Commit | Author | Date | Subject |",
        "|--------|--------|------|---------|",
    ]
    for sha, author, date, subject in commits:
        subject = subject.replace("|", "/")
        lines.append(f"| `{sha}` | {author} | {date} | {subject} |")
    lines.append("")

    summary = "\n".join(lines)
    with open("INCOMING_REPORT.md", "w", encoding="utf-8") as fh:
        fh.write(summary)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
