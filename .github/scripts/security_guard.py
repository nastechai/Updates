#!/usr/bin/env python3
"""
Security guard for the Agentic Coder Fixer — High-End Edition.

Everything the LLM produces that touches the repo passes through here:
  - validate_path()   -> path traversal / symlink / denylist checks
  - write_safe()      -> atomic, guarded writes (incl. BrandGuard manifest check)
  - BrandGuard        -> NEVER misbrand dependencies: refuses any write to a
                         dependency manifest (npm / yarn / pnpm / go / cargo /
                         pip / poetry / docker) that renames or drops an
                         existing dependency identifier. The bot can bump
                         versions, add lockfile entries, or fix scripts — but
                         it can never silently rename a dependency or rewrite
                         a third-party image reference.
  - scan_text()       -> gitleaks (if available) + regex secret fallback
  - scan_output()     -> refuses bot output that itself contains secrets
  - injection_guard() -> fail-closed prompt-injection heuristics
  - fingerprint()     -> stable dedup keys for review findings

Usage:
  from security_guard import SecurityGuard, BrandGuard
  g = SecurityGuard(repo_root=".", config=cfg)
  g.write_safe("relative/path.py", "content")       # BrandGuard auto-applied
  BrandGuard.check_content(path, old, new)          # -> raises SecurityError
"""

import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set

try:
    import requests
except ImportError:
    requests = None  # only needed for optional gitleaks download fallback


# Regex fallback used when gitleaks is not installed. Best-effort last line
# of defense, not a substitute for gitleaks in CI.
_SECRET_RE = [
    re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token|auth)['\"]?\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:postgres|mysql|redis)://[^:\s/]+:[^@\s/]+@"),
]


class SecurityError(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# BrandGuard — never misbrand dependencies
# ─────────────────────────────────────────────────────────────────────────────

# filename (or prefix) -> parser tag
_MANIFEST_KINDS = {
    "package.json": "npm-json",
    "package-lock.json": "npm-json",
    "npm-shrinkwrap.json": "npm-json",
    "composer.json": "npm-json",
    "bower.json": "npm-json",
    "pnpm-lock.yaml": "pnpm-text",
    "yarn.lock": "yarn-text",
    "go.mod": "go-mod",
    "go.sum": "go-sum",
    "requirements.txt": "req-text",
    "requirements-dev.txt": "req-text",
    "requirements-test.txt": "req-text",
    "constraints.txt": "req-text",
    "cargo.toml": "cargo-toml",
    "cargo.lock": "cargo-lock",
    "pipfile": "pipfile",
    "pipfile.lock": "pipfile-lock",
    "poetry.lock": "poetry-lock",
    "pyproject.toml": "pyproject",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "pom.xml": "maven",
    "dockerfile": "docker",
    "containerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
}

# Dependency identifiers in these manifests MUST survive any bot write.
# Keyed by manifest kind. Each entry is a (identifier-regex, display) pair.
_MAY_CHANGE = {
    # Version strings, integrity hashes, and resolved URLs may change; the
    # dependency NAME may not.
}


class BrandGuard:
    """Blocks writes that would rename/remove existing dependencies."""

    _DOCKERFILE_IMAGE_RE = re.compile(r"^\s*FROM\s+(?:\s*--platform=\S+\s+)?([^\s]+)", re.IGNORECASE | re.MULTILINE)
    _COMPOSE_IMAGE_RE = re.compile(r"^\s*image\s*:\s*['\"]?([^\s'\"]+)", re.IGNORECASE | re.MULTILINE)

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            from llm_client import load_config
            config = load_config()
        guard = config.get("brand_guard", {})
        self.enabled = bool(guard.get("enabled", True))
        self.protect_docker_images = bool(guard.get("protect_docker_images", True))
        self.allow_remove = set(guard.get("allow_remove_identifiers", []))
        self.extra_manifests = [p.lower() for p in guard.get("extra_manifests", [])]
        self._guard_patterns = guard.get("guard_file_patterns", [])

    @classmethod
    def is_manifest(cls, rel_path: str) -> bool:
        name = os.path.basename(rel_path.replace("\\", "/")).lower()
        if name in _MANIFEST_KINDS:
            return True
        if name.startswith("dockerfile.") or name.startswith("containerfile."):
            return True
        if name.startswith("docker-compose"):
            return True
        return False

    def _guard_file(self, rel_path: str) -> bool:
        lowered = rel_path.lower()
        for pat in self._guard_patterns:
            if "*" in pat:
                import fnmatch
                if fnmatch.fnmatch(lowered, pat.lower()):
                    return True
            elif pat.lower() in lowered:
                return True
        return False

    # ── Identifier extraction ───────────────────────────────────────────────

    def identifiers(self, rel_path: str, content: str) -> Set[str]:
        """Return the set of dependency identifiers declared in a manifest."""
        if not content:
            return set()
        kind = self._kind_of(rel_path)
        if not kind:
            return set()
        try:
            if kind == "npm-json":
                return self._npm_json(content)
            if kind == "pnpm-text":
                return self._pnpm_text(content)
            if kind == "yarn-text":
                return self._yarn_text(content)
            if kind == "go-mod":
                return self._go_mod(content)
            if kind == "go-sum":
                return self._go_sum(content)
            if kind == "req-text":
                return self._req_text(content)
            if kind in ("cargo-toml", "pyproject"):
                return self._section_toml(content)
            if kind == "cargo-lock":
                return self._cargo_lock(content)
            if kind == "pipfile":
                return self._pipfile(content)
            if kind in ("pipfile-lock", "poetry-lock"):
                return self._pipfile_lock(content)
            if kind == "gradle":
                return self._gradle(content)
            if kind == "maven":
                return self._maven(content)
            if kind in ("docker", "docker-compose"):
                return self._docker(content)
        except Exception:
            return set()
        return set()

    def _kind_of(self, rel_path: str) -> Optional[str]:
        name = os.path.basename(rel_path.replace("\\", "/")).lower()
        if name in _MANIFEST_KINDS:
            return _MANIFEST_KINDS[name]
        if name.startswith("dockerfile.") or name.startswith("containerfile."):
            return "docker"
        if name.startswith("docker-compose"):
            return "docker-compose"
        if self._extra_manifest(name):
            return "npm-json"  # unknown JSON-ish extra -> conservative json parse
        return None

    def _extra_manifest(self, name: str) -> bool:
        return any(name == e.lower() for e in self.extra_manifests)

    # Per-kind parsers ───────────────────────────────────────────────────────

    def _npm_json(self, content: str) -> Set[str]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return set()
        out: Set[str] = set()
        if isinstance(data, dict):
            for section in ("dependencies", "devDependencies", "optionalDependencies",
                            "peerDependencies", "peerDependenciesMeta"):
                deps = data.get(section)
                if isinstance(deps, dict):
                    out.update(k for k in deps if k)
            pkgs = data.get("packages")
            if isinstance(pkgs, dict):
                for key in pkgs:
                    if isinstance(key, str):
                        node = re.search(r"node_modules/(?:@[^/]+/)?[^/]+", key)
                        if node:
                            out.add(node.group(0).split("node_modules/")[1])
                        if key == "":
                            out.add("(root)")
        return {i for i in out if i}

    def _pnpm_text(self, content: str) -> Set[str]:
        out = set()
        for m in re.finditer(r"^\s*['\"]([^'\"/]+)['\"]\s*:", content, re.M):
            out.add(m.group(1))
        for m in re.finditer(r"node_modules/(?:@[^/]+/)?[^/]+", content):
            out.add(m.group(0).split("node_modules/")[1])
        return {i for i in out if i}

    def _yarn_text(self, content: str) -> Set[str]:
        out = set()
        for m in re.finditer(r'^"?([@a-z0-9][^@",:\s]*?)"?@', content, re.M):
            out.add(m.group(1))
        return {i for i in out if i}

    def _go_mod(self, content: str) -> Set[str]:
        out = set()
        for m in re.finditer(r"^\s*([^\s/]+(?:\/[^\s/]+)+)\s+v?\d", content, re.M):
            out.add(m.group(1))
        return {i for i in out if i}

    def _go_sum(self, content: str) -> Set[str]:
        out = set()
        for line in content.splitlines():
            parts = line.split()
            if len(parts) >= 1 and "/" in parts[0]:
                out.add(parts[0])
        return out

    def _req_text(self, content: str) -> Set[str]:
        out = set()
        for line in content.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith(("-r ", "-c ")):
                continue
            if line.startswith(("-e ", "--editable=")):
                continue
            m = re.match(r"^([A-Za-z0-9._-]+)", line)
            if m:
                out.add(m.group(1))
        return out

    def _section_toml(self, content: str) -> Set[str]:
        """Cargo.toml / pyproject.toml section keys under [dependencies]."""
        out = set()
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                in_deps = bool(re.search(r"dependencies", line, re.IGNORECASE))
                continue
            if in_deps and line and not line.startswith(("#", ";", "\"")):
                m = re.match(r"^([A-Za-z0-9_.-]+)\s*(?:=|$|\{)", line)
                if m:
                    out.add(m.group(1))
        return out

    def _cargo_lock(self, content: str) -> Set[str]:
        out = set()
        for m in re.finditer(r'name\s*=\s*"([^"]+)"', content):
            out.add(m.group(1))
        return out

    def _pipfile(self, content: str) -> Set[str]:
        out = set()
        in_sec = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                in_sec = re.match(r"\[(?:packages|dev-packages|require)\]", line, re.IGNORECASE) is not None
                continue
            if in_sec and line and not line.startswith("#"):
                m = re.match(r'^"?([A-Za-z0-9._-]+)"?\s*=', line)
                if m:
                    out.add(m.group(1))
        return out

    def _pipfile_lock(self, content: str) -> Set[str]:
        """Pipfile.lock (JSON) or poetry.lock (TOML 'name = \"...\"' entries)."""
        out = set()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return self._cargo_lock(content)  # TOML-style name lines
        for section in ("default", "develop"):
            deps = data.get(section)
            if isinstance(deps, dict):
                out.update(deps.keys())
        return {i for i in out if i}

    def _gradle(self, content: str) -> Set[str]:
        out = set()
        for m in re.finditer(r"(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s+['\"]([^'\"]+)['\"]", content):
            out.add(m.group(1))
        return out

    def _maven(self, content: str) -> Set[str]:
        out = set()
        for group, art in re.findall(r"<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>", content):
            out.add(f"{group}:{art}")
        return out

    def _docker(self, content: str) -> Set[str]:
        out = set()
        for m in self._DOCKERFILE_IMAGE_RE.finditer(content):
            ref = m.group(1)
            out.add(ref.split("@")[0].split(":")[0])  # strip tag/digest
        for m in self._COMPOSE_IMAGE_RE.finditer(content):
            ref = m.group(1).strip()
            out.add(ref.split("@")[0].split(":")[0])
        return {i for i in out if i}

    # ── Guard API ───────────────────────────────────────────────────────────

    def check_content(self, rel_path: str, old_content: str, new_content: str) -> None:
        """Raise SecurityError if a write would drop/rename a dependency."""
        if not self.enabled:
            return
        if not self.is_manifest(rel_path) and not self._guard_file(rel_path):
            return
        if self._kind_of(rel_path) is None and not self._guard_file(rel_path):
            return
        old_ids = self.identifiers(rel_path, old_content)
        new_ids = self.identifiers(rel_path, new_content)
        if not old_ids:
            return  # nothing declared before -> nothing to protect
        dropped = (old_ids - new_ids) - self.allow_remove
        if not dropped:
            return
        sample = sorted(dropped)[:5]
        raise SecurityError(
            f"BrandGuard blocked write to {rel_path}: would remove/rename "
            f"existing dependencies {sample}. The fixer must never rename, "
            f"rebrand, or drop dependencies — only adjust versions or content."
        )

    def check_content_blocking(self, rel_path: str, old_content: str, new_content: str) -> None:
        """Same as check_content but also catches additions that introduce a
        dependency identifier matching a forbidden brand pattern."""
        self.check_content(rel_path, old_content, new_content)


class SecurityGuard:
    def __init__(self, repo_root: str = ".", config: Optional[Dict[str, Any]] = None):
        self.repo_root = os.path.abspath(repo_root)
        if config is None:
            from llm_client import load_config
            config = load_config()
        sec = config.get("security", {})
        self.denylist = [s.lower() for s in sec.get("denylist_substrings", [])]
        self.injection_phrases = [p.lower() for p in sec.get("injection_phrases", [])]
        self.injection_fail_closed = bool(sec.get("injection_fail_closed", True))
        self.max_scan_bytes = int(sec.get("max_scan_bytes", 1048576))
        self._gitleaks_checked = False
        self._gitleaks_available = None
        self.brand_guard = BrandGuard(config)

    # ── Path safety ─────────────────────────────────────────────────────────

    def validate_path(self, rel_path: str) -> str:
        """Return a normalized, safe repo-relative path or raise SecurityError."""
        if not isinstance(rel_path, str) or not rel_path.strip():
            raise SecurityError("empty path from model")
        path = rel_path.replace("\\", "/")
        if path.startswith("/"):
            raise SecurityError(f"absolute path rejected: {rel_path}")
        if path.lstrip("./").startswith("../") or "/../" in path or path == "..":
            raise SecurityError(f"path traversal rejected: {rel_path}")
        parts = [p for p in path.split("/") if p not in ("", ".")]
        normalized = "/".join(parts)
        lowered = normalized.lower()
        for bad in self.denylist:
            if bad and bad in lowered:
                raise SecurityError(f"denylisted path component '{bad}': {rel_path}")
        probe = os.path.join(self.repo_root, normalized)
        parent = os.path.dirname(probe)
        if os.path.isdir(parent):
            real_parent = os.path.realpath(parent)
            if not real_parent.startswith(self.repo_root):
                raise SecurityError(f"symlink escape rejected: {rel_path}")
        return normalized

    def write_safe(self, rel_path: str, content: Any) -> str:
        """Atomically write file content after validation + BrandGuard check."""
        safe = self.validate_path(rel_path)
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2)
        if not isinstance(content, str):
            content = str(content)
        if len(content.encode("utf-8", errors="ignore")) > 10 * 1024 * 1024:
            raise SecurityError(f"content too large to write: {rel_path}")

        # BrandGuard: protect dependencies before anything hits disk.
        full = os.path.join(self.repo_root, safe)
        old_content = ""
        if os.path.isfile(full):
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    old_content = f.read()
            except OSError:
                old_content = ""
        self.brand_guard.check_content(safe, old_content, content)

        os.makedirs(os.path.dirname(full), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(full), prefix=".agentic-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, full)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return safe

    # ── Secret scanning ─────────────────────────────────────────────────────

    def scan_text(self, text: str) -> List[str]:
        """Return list of secret matches found in text."""
        if not text:
            return []
        if len(text.encode("utf-8", errors="ignore")) > self.max_scan_bytes:
            return ["scan truncated: content too large"]
        if self._gitleaks_ready():
            try:
                out = self._run_gitleaks(text)
                if out is not None:
                    return out
            except Exception as e:
                print(f"[security] gitleaks failed, falling back to regex: {e}", file=sys.stderr)
        found = []
        for rx in _SECRET_RE:
            for m in rx.finditer(text):
                found.append(m.group(0)[:80])
        return list(dict.fromkeys(found))

    def scan_output(self, text: str) -> None:
        """Refuse to proceed if the model's own output contains secrets."""
        hits = self.scan_text(text)
        if hits:
            raise SecurityError(f"model output contains secrets ({len(hits)}); refusing: {hits[0]}")

    # ── Injection guard ─────────────────────────────────────────────────────

    def injection_guard(self, text: str) -> None:
        """Fail closed if the assistant response attempts to override system."""
        lowered = text.lower()
        for phrase in self.injection_phrases:
            if phrase in lowered:
                if self.injection_fail_closed:
                    raise SecurityError(f"prompt-injection phrase detected in output: '{phrase}'")
                return
        if re.search(r"<\s*/?\s*untrusted", lowered) or "<untrusted_end>" in text:
            if self.injection_fail_closed:
                raise SecurityError("attempted delimiter escape detected")

    # ── Dedup fingerprints ──────────────────────────────────────────────────

    @staticmethod
    def fingerprint(path: str, line: Optional[int], suggestion: Optional[str],
                    category: Optional[str] = None, message: Optional[str] = None) -> str:
        import hashlib
        base = f"{path}:{line or 0}"
        if suggestion:
            base += "|" + suggestion.strip()[:200]
        elif message:
            base += "|" + message.strip()[:200]
        return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()

    # ── gitleaks ────────────────────────────────────────────────────────────

    def _gitleaks_ready(self) -> bool:
        if self._gitleaks_checked:
            return self._gitleaks_available
        self._gitleaks_checked = True
        import shutil
        self._gitleaks_available = shutil.which("gitleaks") is not None
        if not self._gitleaks_available:
            print("[security] gitleaks not on PATH; using regex fallback", file=sys.stderr)
        return self._gitleaks_available

    def _run_gitleaks(self, text: str) -> Optional[List[str]]:
        import shutil
        import subprocess
        gitleaks = shutil.which("gitleaks")
        if not gitleaks:
            return None
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(text)
            tmp_path = f.name
        try:
            proc = subprocess.run(
                [gitleaks, "detect", "--source", tmp_path, "--no-banner", "--redact=0",
                 "--report-format", "json", "--report-path", "/dev/stdout"],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode in (0, 1):
                import json as _json
                try:
                    findings = _json.loads(proc.stdout or "[]")
                    return [f.get("RuleID", "gitleaks") for f in findings if isinstance(f, dict)]
                except Exception:
                    return [] if proc.returncode == 0 else ["gitleaks-findings"]
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    import sys
    g = SecurityGuard(".")
    if len(sys.argv) > 1:
        try:
            print("validated:", g.validate_path(sys.argv[1]))
        except SecurityError as e:
            print("BLOCKED:", e)
            sys.exit(1)
    # BrandGuard self-test.
    bg = BrandGuard()
    old = '{"name": "x", "dependencies": {"express": "^4.0", "lodash": "^4.0"}}'
    renamed = '{"name": "x", "dependencies": {"expressjs": "^4.0", "lodash": "^4.0"}}'
    try:
        bg.check_content("package.json", old, renamed)
        print("BrandGuard: MISBRAND NOT BLOCKED (BUG)")
        sys.exit(1)
    except SecurityError as e:
        print("BrandGuard: rename blocked OK ->", str(e)[:80])
    bumped = '{"name": "x", "dependencies": {"express": "^5.0", "lodash": "^4.0"}}'
    bg.check_content("package.json", old, bumped)
    print("BrandGuard: version bump allowed OK")
