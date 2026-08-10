#!/usr/bin/env python3
"""
PR review agent for the Agentic Coder Fixer.

Reviews a pull request using Ollama (via OpenAI-compatible API) and:
  - Resolves per-file review skills (SKILL.md registry)
  - Does delta reviews (only files changed since the last review)
  - Deduplicates findings across pushes (hidden marker comment)
  - Posts inline review comments with suggestion blocks
  - Sets the review event (COMMENT / REQUEST_CHANGES) by severity
  - Creates/updates an 'agentic-review' check run (merge gate)

Usage:
  python review_agent.py --pr 123 [--repo owner/repo] [--token TOKEN]
  Requires env: NAS_TOKEN or GITHUB_TOKEN, OLLAMA_API_KEY_*
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    sys.stderr.write("review_agent requires `requests`\n")
    raise

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from llm_client import LLMClient, load_config  # noqa: E402
from skills_loader import SkillsRegistry  # noqa: E402
from security_guard import BrandGuard, SecurityGuard, SecurityError  # noqa: E402

API = "https://api.github.com"
STATE_PREFIX = "<!-- agentic-review-state:"
SEVERITY_RANK = {"info": 0, "minor": 1, "major": 2, "critical": 3}


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        self.owner, self.repo = owner, repo
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        return f"{API}/repos/{self.owner}/{self.repo}{path}"

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        for attempt in range(4):
            resp = self.session.get(self._url(path), headers=self.headers, params=params, timeout=60)
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"GET {path} failed after retries")

    def get_all(self, path: str, params: Optional[Dict] = None) -> List[Any]:
        items, page = [], 1
        while True:
            batch = self.get(path, params={**(params or {}), "per_page": 100, "page": page})
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1

    def post(self, path: str, payload: Any, retries: int = 3) -> requests.Response:
        for attempt in range(retries):
            resp = self.session.post(self._url(path), headers=self.headers, json=payload, timeout=60)
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            return resp
        return resp

    def patch(self, path: str, payload: Any, retries: int = 3) -> requests.Response:
        for attempt in range(retries):
            resp = self.session.patch(self._url(path), headers=self.headers, json=payload, timeout=60)
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            return resp
        return resp

    def put(self, path: str, payload: Any, retries: int = 3) -> requests.Response:
        for attempt in range(retries):
            resp = self.session.put(self._url(path), headers=self.headers, json=payload, timeout=60)
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            return resp
        return resp


def build_system_prompt(registry: SkillsRegistry, agents_md: str, cfg: Dict) -> str:
    parts = [
        "You are the NasTech Agentic Coder Fixer review agent.",
        "You review pull request diffs and report findings as JSON.",
        "Rules:",
        "1. Only flag real bugs, security issues, and performance problems with an attack path or failure mode.",
        "2. Do NOT flag cosmetic style, or branding/renaming issues (a separate pipeline owns branding).",
        "3. Do NOT invent findings; if the diff is clean, return an empty findings array.",
        "4. Line numbers must be from the NEW version of the file (right side of the diff).",
        "5. Keep messages concise and actionable. Include a concrete 'suggestion' snippet when possible.",
        f"6. Severity threshold: report at most {cfg['review'].get('max_findings', 30)} findings.",
        "",
        "## Dependency branding — HARD RULES (never violate):",
        "1. NEVER suggest renaming, rebranding, or re-scoping any dependency.",
        "2. In package.json/lockfiles/go.mod/Cargo.toml/requirements.txt etc., dependency NAMES are immutable.",
        "3. NEVER suggest rewriting a third-party Docker base image (`FROM python`, `node`, `alpine`, `ghcr.io/*`, etc.) to a branded image.",
        "4. Only the project's OWN identity may carry NasTech branding (the branding pipeline owns that and is validated by BrandGuard).",
        "5. If a finding would only change branding/renaming, do NOT report it — BrandGuard blocks those writes and it is noise.",
        "",
        "## Skills registry (load only what is relevant):",
        registry.describe_all(),
    ]
    if agents_md:
        parts.append("\n## Repository AGENTS.md (must follow):\n" + agents_md[:8000])
    return "\n".join(parts)


def build_review_prompt(pr: Dict, files: List[Dict], skill_text: str) -> str:
    head = (
        f"# PR #{pr['number']}: {pr.get('title', '')}\n"
        f"Author: {pr['user']['login']}\n"
        f"Base: {pr['base']['ref']} <- Head: {pr['head']['ref']} ({pr['head']['sha'][:12]})\n"
        f"Body:\n{pr.get('body') or '(none)'}\n"
    )
    if skill_text:
        head += f"\n## Review criteria to apply\n{skill_text}\n"
    head += (
        "\n## Instructions\n"
        'Output a single JSON object: {"summary": "...", "findings": ['
        '{"path": "...", "line": int, "severity": "critical|major|minor|info", '
        '"category": "bug|security|performance|maintainability|style|docs|test", '
        '"confidence": 0.0-1.0, "message": "...", "suggestion": "..."}]}\n'
        "Line must be the right-side (new file) line number, or null if not applicable.\n"
    )
    blocks = []
    for f in files:
        blocks.append(f"<untrusted file_path=\"{f['filename']}\" status=\"{f.get('status')}\" language=\"{f.get('language', '')}\">\n{f.get('patch') or '(no diff shown)'}\n</untrusted>")
    return head + "\n" + "\n".join(blocks) + "\n\n<untrusted_end>"


class ReviewAgent:
    def __init__(self, owner: str, repo: str, token: str, pr_number: int, cfg: Dict):
        self.gh = GitHubClient(token, owner, repo)
        self.pr_number = pr_number
        self.cfg = cfg
        self.client = LLMClient(cfg)
        self.security = SecurityGuard(config=cfg)
        self.brand_guard = self.security.brand_guard
        rev = cfg.get("review", {})
        self.skills_dir = os.path.join(os.path.dirname(ROOT), cfg.get("skills", {}).get("dir", ".github/skills"))
        self.registry = SkillsRegistry(self.skills_dir)
        self.check_name = rev.get("check_name", "agentic-review")
        self.threshold = rev.get("severity_threshold", "critical")
        self.min_confidence = float(rev.get("min_confidence", 0.6))
        self.max_findings = int(rev.get("max_findings", 30))
        self.skip_authors = rev.get("skip_authors", [])

    # ── Main ────────────────────────────────────────────────────────────────

    def run(self) -> int:
        pr = self.gh.get(f"/pulls/{self.pr_number}")
        author = pr["user"]["login"]
        if author in self.skip_authors:
            print(f"[review] skipping author {author}")
            return 0
        if pr.get("draft") and not self.cfg.get("review", {}).get("review_drafts", False):
            print("[review] skipping draft PR")
            return 0

        head_sha = pr["head"]["sha"]
        state = self._read_state(pr["issue_url"].rsplit("/", 1)[1])
        prev_sha = state.get("head_sha")
        fingerprints = set(state.get("fingerprints", []))

        # Delta review: only files changed since the last reviewed sha.
        files = self._changed_files(pr, prev_sha)
        if not files:
            print(f"[review] no changed files since {prev_sha or 'baseline'}")
            self._update_check_run(head_sha, "success", "No changes since last review.")
            return 0

        agents_md = self._read_agents_md()
        skills_text = self._collect_skills(files)
        system = build_system_prompt(self.registry, agents_md, self.cfg)
        prompt = build_review_prompt(pr, files, skills_text)

        print(f"[review] reviewing {len(files)} files, head {head_sha[:12]}, delta={bool(prev_sha)}")
        result = self.client.call_json(prompt, system=system, temperature=0.2)
        if result is None:
            print("[review] LLM returned no parseable result")
            return 1

        findings = self._sanitize_findings(result, files, fingerprints)
        findings = [f for f in findings if not self._manifest_brand_risk(f)]
        if not findings:
            print("[review] no new findings")
            self._update_check_run(head_sha, "success", "No actionable findings.")
            self._write_state(pr["issue_url"].rsplit("/", 1)[1], head_sha, fingerprints)
            return 0

        verdict = self._post_review(pr, findings)
        self._update_check_run(head_sha, "failure" if verdict == "changes_requested" else "success",
                               f"{len(findings)} finding(s), event={verdict}")
        self._write_state(pr["issue_url"].rsplit("/", 1)[1], head_sha, fingerprints | {f["fingerprint"] for f in findings})
        print(f"[review] posted {len(findings)} finding(s) as {verdict}")
        return 0

    # ── Data gathering ──────────────────────────────────────────────────────

    def _changed_files(self, pr: Dict, prev_sha: Optional[str]) -> List[Dict]:
        if prev_sha and prev_sha != pr["head"]["sha"]:
            try:
                cmp = self.gh.get(f"/compare/{prev_sha}...{pr['head']['sha']}")
                return [f for f in cmp.get("files", []) if f.get("patch")]
            except Exception as e:
                print(f"[review] delta compare failed ({e}); falling back to full diff")
        return self.gh.get_all(f"/pulls/{self.pr_number}/files")

    def _read_agents_md(self) -> str:
        try:
            with open(os.path.join(os.getcwd(), "AGENTS.md"), "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def _collect_skills(self, files: List[Dict]) -> str:
        keys: List[str] = []
        for f in files:
            for key in self.registry.resolve(f["filename"]):
                if key not in keys:
                    keys.append(key)
        for always in self.cfg.get("skills", {}).get("always_load", []):
            if always not in keys:
                keys.append(always)
        return self.registry.get_bodies(keys)

    # ── Finding handling ────────────────────────────────────────────────────

    def _sanitize_findings(self, result: Any, files: List[Dict],
                           fingerprints: set) -> List[Dict]:
        known_paths = {f["filename"] for f in files}
        out = []
        for raw in result.get("findings", []) if isinstance(result, dict) else []:
            if not isinstance(raw, dict):
                continue
            path = raw.get("path")
            if path not in known_paths:
                continue
            try:
                path = self.security.validate_path(path)
            except SecurityError:
                continue
            severity = raw.get("severity", "minor")
            if severity not in SEVERITY_RANK:
                severity = "minor"
            try:
                confidence = float(raw.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0
            if confidence < self.min_confidence:
                continue
            fp = SecurityGuard.fingerprint(path, raw.get("line"), raw.get("suggestion"),
                                           raw.get("category"), raw.get("message"))
            if fp in fingerprints:
                continue
            out.append({
                "path": path,
                "line": raw.get("line"),
                "severity": severity,
                "category": raw.get("category", "bug"),
                "confidence": confidence,
                "message": str(raw.get("message", ""))[:2000],
                "suggestion": str(raw.get("suggestion", ""))[:2000],
                "fingerprint": fp,
            })
            if len(out) >= self.max_findings:
                break
        return out

    def _manifest_brand_risk(self, finding: Dict) -> bool:
        """Suppress findings that suggest renaming/rebranding an existing dependency."""
        path = finding.get("path", "")
        if not BrandGuard.is_manifest(path):
            return False
        full = os.path.join(os.getcwd(), path)
        if not os.path.isfile(full):
            return False
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                old = f.read()
        except OSError:
            return False
        ids = self.brand_guard.identifiers(path, old)
        if not ids:
            return False
        text = f"{finding.get('message', '')} {finding.get('suggestion', '')}".lower()
        if not any(kw in text for kw in ("rename", "rebrand", "misbrand", "re-scope", "rename to", "instead of")):
            return False
        for ident in ids:
            if ident.lower() in text:
                return True
        return False

    def _post_review(self, pr: Dict, findings: List[Dict]) -> str:
        any_critical = any(SEVERITY_RANK[f["severity"]] >= SEVERITY_RANK.get(self.threshold, 3) for f in findings)
        event = "REQUEST_CHANGES" if any_critical else "COMMENT"

        comments = []
        for f in findings:
            body = f"**[{f['severity']}] {f['category']}**\n\n{f['message']}"
            if f["suggestion"]:
                body += f"\n\n```suggestion\n{f['suggestion']}\n```"
            c = {"path": f["path"], "side": "RIGHT", "body": body}
            if isinstance(f["line"], int) and f["line"] > 0:
                c["line"] = f["line"]
            comments.append(c)

        summary = self._summarize(findings)
        payload = {
            "event": event,
            "body": f"## Agentic Review ({len(findings)} finding(s))\n\n{summary}\n\n---\n_Run by NasTech Agentic Coder Fixer._",
        }
        if comments:
            payload["comments"] = comments

        try:
            resp = self.gh.post(f"/pulls/{self.pr_number}/reviews", payload)
        except requests.HTTPError as e:
            print(f"[review] review post failed ({e}); falling back to comment")
            self.gh.post(f"/issues/{self.pr_number}/comments",
                         {"body": payload["body"] + "\n\n_Could not post inline comments._"})
            return event.lower()

        if resp.status_code == 422:
            # Inline positions may be stale; post individually and keep survivors.
            ok = 0
            for c in comments:
                r = self.gh.post(f"/pulls/{self.pr_number}/reviews",
                                 {"event": event, "comments": [c]})
                if r.status_code < 300:
                    ok += 1
            print(f"[review] inline fallback posted {ok}/{len(comments)}")
            self.gh.post(f"/issues/{self.pr_number}/comments", {"body": payload["body"]})
        return event.lower()

    @staticmethod
    def _summarize(findings: List[Dict]) -> str:
        by_sev: Dict[str, int] = {}
        for f in findings:
            by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        parts = [f"- **{sev}**: {cnt}" for sev, cnt in sorted(by_sev.items(), key=lambda kv: -SEVERITY_RANK[kv[0]])]
        return "\n".join(parts) if parts else "No findings."

    # ── State (delta + dedup via hidden marker comment) ─────────────────────

    def _state_comment_id(self, issue_number: int) -> Optional[int]:
        for c in self.gh.get_all(f"/issues/{issue_number}/comments"):
            if c.get("body", "").startswith(STATE_PREFIX):
                return c["id"]
        return None

    def _read_state(self, issue_number: int) -> Dict:
        try:
            cid = self._state_comment_id(issue_number)
            if cid is None:
                return {}
            for c in self.gh.get_all(f"/issues/{issue_number}/comments"):
                if c["id"] == cid:
                    body = c["body"]
                    data = body[len(STATE_PREFIX):]
                    data = data[: data.find(" -->")]
                    return json.loads(data)
        except Exception as e:
            print(f"[review] state read failed: {e}")
        return {}

    def _write_state(self, issue_number: int, head_sha: str, fingerprints: set) -> None:
        payload = json.dumps({"head_sha": head_sha, "fingerprints": sorted(fingerprints)})
        body = f"{STATE_PREFIX}{payload} -->"
        try:
            cid = self._state_comment_id(issue_number)
            if cid is not None:
                self.gh.patch(f"/issues/comments/{cid}", {"body": body})
            else:
                self.gh.post(f"/issues/{issue_number}/comments", {"body": body})
        except Exception as e:
            print(f"[review] state write failed (non-fatal): {e}")

    def _update_check_run(self, head_sha: str, conclusion: str, summary: str) -> None:
        try:
            payload = {
                "name": self.check_name,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": conclusion,
                "output": {"title": f"Agentic Review: {conclusion}", "summary": summary[:5000]},
            }
            self.gh.post("/check-runs", payload)
        except Exception as e:
            print(f"[review] check-run update failed (non-fatal): {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic PR review agent")
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/repo")
    parser.add_argument("--token", default=os.environ.get("NAS_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    args = parser.parse_args()

    if not args.repo or "/" not in args.repo:
        print("--repo owner/repo required")
        return 1
    if not args.token:
        print("token required (NAS_TOKEN or GITHUB_TOKEN)")
        return 1

    owner, repo = args.repo.split("/", 1)
    cfg = load_config()
    agent = ReviewAgent(owner, repo, args.token, int(args.pr), cfg)
    print(f"[review] model: {agent.client.describe()}")
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
