"""Tests for the local release helper."""

import pytest

from tools.release import (
    bump_version,
    replace_init_version,
    replace_pyproject_version,
    resolve_target_version,
)


def test_bump_version_patch():
    assert bump_version("0.2.0", "patch") == "0.2.1"


def test_bump_version_minor():
    assert bump_version("0.2.0", "minor") == "0.3.0"


def test_bump_version_major():
    assert bump_version("0.2.0", "major") == "1.0.0"


def test_bump_version_rejects_invalid_semver():
    with pytest.raises(ValueError, match="semantic version"):
        bump_version("0.2", "patch")


def test_replace_pyproject_version():
    text = '[project]\nname = "huntsman-mcp"\nversion = "0.2.0"\n'
    updated = replace_pyproject_version(text, "0.2.1")
    assert 'version = "0.2.1"' in updated
    assert 'version = "0.2.0"' not in updated


def test_replace_init_version():
    text = '__version__ = "0.2.0"\n'
    updated = replace_init_version(text, "0.2.1")
    assert '__version__ = "0.2.1"' in updated
    assert '__version__ = "0.2.0"' not in updated


def test_resolve_target_version_prefers_explicit_version():
    assert resolve_target_version("0.2.0", explicit_version="0.2.5", bump=None) == "0.2.5"


def test_resolve_target_version_uses_patch_by_default():
    assert resolve_target_version("0.2.0", explicit_version=None, bump=None) == "0.2.1"
