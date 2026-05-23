"""Local release helper for version bumps and tag-driven PyPI publishes."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
INIT_PATH = ROOT / "huntsman_mcp" / "__init__.py"

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^version = "([^"]+)"$')
INIT_VERSION_RE = re.compile(r'(?m)^__version__ = "([^"]+)"$')


def bump_version(version: str, part: str) -> str:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ValueError(f"Expected a semantic version like 0.2.0, got {version!r}.")

    major, minor, patch = (int(piece) for piece in match.groups())

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump part {part!r}.")

    return f"{major}.{minor}.{patch}"


def resolve_target_version(
    current_version: str,
    *,
    explicit_version: str | None,
    bump: str | None,
) -> str:
    if explicit_version:
        if not SEMVER_RE.fullmatch(explicit_version):
            raise ValueError(
                f"Expected a semantic version like 0.2.1, got {explicit_version!r}."
            )
        return explicit_version

    return bump_version(current_version, bump or "patch")


def replace_pyproject_version(text: str, new_version: str) -> str:
    updated, count = PYPROJECT_VERSION_RE.subn(f'version = "{new_version}"', text, count=1)
    if count != 1:
        raise ValueError("Could not find exactly one version field in pyproject.toml.")
    return updated


def replace_init_version(text: str, new_version: str) -> str:
    updated, count = INIT_VERSION_RE.subn(f'__version__ = "{new_version}"', text, count=1)
    if count != 1:
        raise ValueError("Could not find exactly one __version__ field in huntsman_mcp/__init__.py.")
    return updated


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def _git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _ensure_clean_tree() -> None:
    status = _git_output("status", "--short")
    if status:
        raise SystemExit("Working tree is not clean. Commit or stash changes before releasing.")


def _ensure_main_branch() -> None:
    branch = _git_output("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise SystemExit(f"Release helper must run from main. Current branch: {branch}")


def _current_versions() -> tuple[str, str]:
    pyproject_text = PYPROJECT_PATH.read_text()
    init_text = INIT_PATH.read_text()

    pyproject_match = PYPROJECT_VERSION_RE.search(pyproject_text)
    init_match = INIT_VERSION_RE.search(init_text)
    if not pyproject_match or not init_match:
        raise SystemExit("Could not read current versions from pyproject.toml and huntsman_mcp/__init__.py.")

    return pyproject_match.group(1), init_match.group(1)


def _write_version_files(new_version: str) -> None:
    PYPROJECT_PATH.write_text(
        replace_pyproject_version(PYPROJECT_PATH.read_text(), new_version)
    )
    INIT_PATH.write_text(
        replace_init_version(INIT_PATH.read_text(), new_version)
    )


def _run_tests() -> None:
    if shutil.which("uv"):
        _run(["uv", "run", "pytest", "-q"])
        return
    _run([sys.executable, "-m", "pytest", "-q"])


def _build_dist() -> None:
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    if shutil.which("uv"):
        _run(["uv", "build"])
        return
    _run([sys.executable, "-m", "build"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump version, verify, commit, tag, and optionally push a Huntsman release."
    )
    parser.add_argument("--version", help="Explicit target version, e.g. 0.2.1")
    parser.add_argument(
        "--bump",
        choices=["patch", "minor", "major"],
        help="Semver segment to bump. Defaults to patch when --version is omitted.",
    )
    parser.add_argument("--no-commit", action="store_true", help="Skip git commit creation.")
    parser.add_argument("--no-tag", action="store_true", help="Skip creating the git tag.")
    parser.add_argument("--no-push", action="store_true", help="Skip pushing main and the release tag.")
    args = parser.parse_args()

    _ensure_clean_tree()
    _ensure_main_branch()

    pyproject_version, init_version = _current_versions()
    if pyproject_version != init_version:
        raise SystemExit(
            "Version mismatch between pyproject.toml and huntsman_mcp/__init__.py."
        )

    target_version = resolve_target_version(
        pyproject_version,
        explicit_version=args.version,
        bump=args.bump,
    )
    tag_name = f"v{target_version}"

    existing_tags = _git_output("tag", "--list", tag_name)
    if existing_tags:
        raise SystemExit(f"Tag {tag_name} already exists.")

    _write_version_files(target_version)
    _run_tests()
    _build_dist()

    _run(["git", "add", "pyproject.toml", "huntsman_mcp/__init__.py"])

    if not args.no_commit:
        _run(["git", "commit", "-m", f"Release v{target_version}"])

    if not args.no_tag:
        _run(["git", "tag", tag_name])

    if not args.no_push:
        _run(["git", "push", "origin", "main"])
        if not args.no_tag:
            _run(["git", "push", "origin", tag_name])

    print(f"Release helper prepared version {target_version}.")


if __name__ == "__main__":
    main()
