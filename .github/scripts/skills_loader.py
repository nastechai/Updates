#!/usr/bin/env python3
"""
Skills registry for the Agentic Coder Fixer.

Loads the SKILL.md format (the open Agent Skills standard) from a directory
tree, builds a cheap registry index from frontmatter only, and resolves which
skills apply to a given changed file. Bodies are loaded lazily so the model
only sees skill instructions that are actually relevant.

Resolution order (first match wins):
  1. Special CI/infra paths (Dockerfile, .github/workflows/*, Jenkinsfile, ...)
  2. Built-in extension map
  3. Shebang of extensionless scripts
  4. Registry fallback: a skill's frontmatter `metadata.extensions`

Usage:
  from skills_loader import SkillsRegistry
  reg = SkillsRegistry(".github/skills")
  for f in changed_files:
      keys = reg.resolve(f)
      bodies = reg.get_bodies(keys)
"""

import os
import re
from typing import Dict, List, Optional, Tuple

# ── Frontmatter parsing ──────────────────────────────────────────────────────

_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_ITEM_RE = re.compile(r"^\s*-\s*(.+?)\s*$")
_KV_RE = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")
_LIST_VALUE_RE = re.compile(r"^\[(.*)\]$")


def _split_list(value: str) -> List[str]:
    value = value.strip()
    m = _LIST_VALUE_RE.match(value)
    if m:
        items = [i.strip().strip("'\"") for i in m.group(1).split(",") if i.strip()]
        return items
    items = []
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            items.append(line[1:].strip().strip("'\"\""))
        else:
            items.append(line.strip().strip("'\"\""))
    return [i for i in items if i]


def parse_skill(content: str) -> Tuple[Dict, str]:
    """Return (frontmatter_dict, body_markdown)."""
    m = _FRONT_RE.match(content)
    if not m:
        return {}, content.strip()
    raw_fm, body = m.group(1), m.group(2)
    fm: Dict = {}
    current_key = None
    for line in raw_fm.splitlines():
        kv = _KV_RE.match(line)
        if kv:
            key, value = kv.group(1), kv.group(2)
            current_key = key
            if value.startswith("[") or "," in value:
                fm[key] = _split_list(value)
            else:
                fm[key] = value.strip().strip("'\"")
        elif _ITEM_RE.match(line) and current_key:
            if not isinstance(fm.get(current_key), list):
                fm[current_key] = []
            fm[current_key].append(_ITEM_RE.match(line).group(1).strip().strip("'\"\""))
    return fm, body.strip()


class SkillsRegistry:
    """Registry index + lazy body loader for SKILL.md files."""

    # Special paths that resolve to a skill regardless of extension.
    SPECIAL_PATHS = {
        "dockerfile": ("docker",),
        "docker-compose.yml": ("docker",),
        "docker-compose.yaml": ("docker",),
        "jenkinsfile": ("jenkins",),
        ".gitlab-ci.yml": ("gitlab-ci",),
        ".travis.yml": ("github-actions",),
        "azure-pipelines.yml": ("github-actions",),
        "makefile": ("shell",),
    }

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self._index: Dict[str, Dict] = {}   # skill_key -> frontmatter
        self._bodies: Dict[str, str] = {}   # skill_key -> body (lazy)
        self._by_ext: Dict[str, str] = {}   # extension -> skill_key
        self._scan()

    def _scan(self) -> None:
        if not os.path.isdir(self.skills_dir):
            return
        for entry in sorted(os.listdir(self.skills_dir)):
            skill_dir = os.path.join(self.skills_dir, entry)
            if not os.path.isdir(skill_dir):
                continue
            skill_file = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isfile(skill_file):
                continue
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    fm, body = parse_skill(f.read())
            except OSError:
                continue
            key = (fm.get("name") or entry).strip()
            if not key:
                continue
            meta = fm.get("metadata", {})
            if isinstance(meta, str):
                meta = {}
            self._index[key] = {"frontmatter": fm, "path": skill_file}
            self._bodies[key] = body
            exts = meta.get("extensions") or meta.get("extensions_") or fm.get("extensions") or []
            if isinstance(exts, str):
                exts = _split_list(exts)
            for ext in exts:
                ext = ext.strip().lstrip("*").lower()
                if ext.startswith(".") or ext:
                    ext = ext if ext.startswith(".") else "." + ext
                    self._by_ext.setdefault(ext, key)

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def skills(self) -> List[str]:
        return sorted(self._index.keys())

    def get_bodies(self, keys: List[str]) -> str:
        """Return concatenated SKILL.md bodies for the given keys."""
        parts = []
        for key in keys:
            body = self._bodies.get(key)
            if body:
                parts.append(f"## Skill: {key}\n{body}")
        return "\n\n".join(parts)

    def get_description(self, key: str) -> str:
        fm = self._index.get(key, {}).get("frontmatter", {})
        return fm.get("description", "")

    def describe_all(self) -> str:
        """Compact registry listing for the system prompt."""
        lines = []
        for key in self.skills:
            desc = self.get_description(key).strip().replace("\n", " ")
            lines.append(f"- {key}: {desc}")
        return "\n".join(lines)

    def resolve(self, rel_path: str) -> List[str]:
        """Resolve a repo-relative file path to a list of skill keys."""
        rel_path = rel_path.replace(os.sep, "/").lstrip("./")
        base = os.path.basename(rel_path).lower()
        dirs = [d.lower() for d in rel_path.split("/")]

        # 1. Special CI/infra paths.
        lower_path = rel_path.lower()
        if lower_path == "dockerfile" or lower_path.startswith("dockerfile."):
            return ["docker", "docker-brand-validator"]
        if lower_path == "docker-compose.yml" or lower_path == "docker-compose.yaml":
            return ["docker", "docker-brand-validator"]
        if lower_path.endswith("jenkinsfile") or base == "jenkinsfile":
            return ["jenkins"]
        if lower_path == ".gitlab-ci.yml":
            return ["gitlab-ci"]
        if base in ("makefile",):
            return ["shell"]
        if base.startswith(".github/workflows/") or rel_path.startswith(".github/workflows/"):
            return ["github-actions"]

        # 1b. Dependency manifests -> brand validators + fixers.
        manifest_skills = self._manifest_skills(base, lower_path)
        if manifest_skills:
            return manifest_skills

        # 2. Extension map.
        _, ext = os.path.splitext(base)
        if ext:
            key = self._by_ext.get(ext.lower())
            if key:
                return [key]

        # 3. Shebang for extensionless scripts.
        if not ext:
            shebang_key = self._shebang_key(rel_path)
            if shebang_key:
                return [shebang_key]

        # 4. Registry fallback via any frontmatter 'when'/'targets' hints is
        #    intentionally not auto-applied (avoid false positives). Callers
        #    can add 'always_load' skills explicitly.
        return []

    # ── Internals ───────────────────────────────────────────────────────────

    _MANIFEST_MAP = {
        "package.json": ["npm-fixer", "npm-brand-validator"],
        "package-lock.json": ["npm-fixer", "npm-brand-validator"],
        "npm-shrinkwrap.json": ["npm-brand-validator"],
        "yarn.lock": ["npm-brand-validator"],
        "pnpm-lock.yaml": ["npm-brand-validator"],
        ".npmrc": ["npm-brand-validator"],
        "bower.json": ["npm-brand-validator"],
        "composer.json": ["npm-brand-validator"],
        "go.mod": ["ecosystem-branding"],
        "go.sum": ["ecosystem-branding"],
        "cargo.toml": ["ecosystem-branding"],
        "cargo.lock": ["ecosystem-branding"],
        "requirements.txt": ["ecosystem-branding"],
        "requirements-dev.txt": ["ecosystem-branding"],
        "requirements-test.txt": ["ecosystem-branding"],
        "constraints.txt": ["ecosystem-branding"],
        "pipfile": ["ecosystem-branding"],
        "pipfile.lock": ["ecosystem-branding"],
        "pyproject.toml": ["ecosystem-branding"],
        "poetry.lock": ["ecosystem-branding"],
        "pom.xml": ["ecosystem-branding"],
        "build.gradle": ["ecosystem-branding"],
        "build.gradle.kts": ["ecosystem-branding"],
    }

    def _manifest_skills(self, base: str, lower_path: str) -> Optional[List[str]]:
        """Resolve dependency manifest files to brand/fix skills."""
        if base in self._MANIFEST_MAP:
            return list(self._MANIFEST_MAP[base])
        # namespaced monorepo lockfiles / nested manifests.
        if base.startswith("package-lock") or base.startswith("yarn.lock"):
            return ["npm-brand-validator"]
        return None

    def _shebang_key(self, rel_path: str) -> Optional[str]:
        full = os.path.join(self.skills_dir, os.pardir, os.pardir, rel_path)
        full = os.path.abspath(full)
        if not os.path.isfile(full):
            return None
        try:
            with open(full, "rb") as f:
                first = f.readline(128).decode("utf-8", errors="ignore").strip()
        except OSError:
            return None
        if not first.startswith("#!"):
            return None
        lowered = first.lower()
        if "python" in lowered:
            return "python"
        if "node" in lowered or "deno" in lowered or "bun" in lowered:
            return "javascript"
        if "bash" in lowered or "sh" in lowered:
            return "shell"
        return None


if __name__ == "__main__":
    import sys
    reg = SkillsRegistry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills"))
    print("Registered skills:", ", ".join(reg.skills))
    for sample in sys.argv[1:]:
        print(f"{sample} -> {reg.resolve(sample)}")
