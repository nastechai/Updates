import os
import pytest
from pathlib import Path

def test_readme_branding():
    """Verify that the README uses NasTech branding."""
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text()
        assert "NasTech" in content
        assert "Hermes" not in content or "sync from Hermes" in content # Allow context references

def test_package_json_branding():
    """Verify that package.json (if it exists) is branded."""
    pkg_path = Path("package.json")
    if pkg_path.exists():
        content = pkg_path.read_text()
        assert "nastech-agent" in content
        assert "hermes-agent" not in content

def test_env_branding():
    """Verify that .env files use NASTECH_ prefix."""
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        assert "NASTECH_" in content
        assert "HERMES_" not in content

def test_source_code_renaming():
    """Verify that directories have been renamed from hermes to nastech."""
    hermes_dirs = list(Path(".").rglob("*hermes*"))
    # Filter out .git and other hidden dirs
    hermes_dirs = [d for d in hermes_dirs if ".git" not in str(d) and ".github" not in str(d)]
    assert len(hermes_dirs) == 0, f"Found directories still containing 'hermes': {hermes_dirs}"

