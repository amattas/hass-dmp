"""Publish the latest tagged revision for each minor documentation version."""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Sequence
from pathlib import Path

from docs_versioning import ReleaseVersion, prepare_release, select_documented_releases

REPO_ROOT = Path(__file__).resolve().parents[1]
MIKE_COMMAND = (
    sys.executable,
    "-c",
    "from mike.driver import main; raise SystemExit(main())",
)


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    user_scheme = "nt_user" if os.name == "nt" else "posix_user"
    script_paths = [
        sysconfig.get_path("scripts"),
        sysconfig.get_path("scripts", scheme=user_scheme),
    ]
    environment["PATH"] = os.pathsep.join(
        [path for path in script_paths if path] + [environment.get("PATH", "")]
    )
    return environment


def _run(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        input=input_text,
        text=True,
        capture_output=capture_output,
        env=_child_environment(),
    )


def _git_output(*args: str) -> str:
    return _run(["git", *args], capture_output=True).stdout.strip()


def _reset_publish_branch(branch: str) -> None:
    if branch != "gh-pages" and not branch.startswith("docs-version-"):
        raise ValueError(
            "Publication branch must be gh-pages or start with docs-version-"
        )

    current_branch = _git_output("branch", "--show-current")
    if current_branch == branch:
        raise ValueError(f"Cannot replace the checked-out branch: {branch}")

    tree = _run(["git", "mktree"], input_text="", capture_output=True).stdout.strip()
    commit = _git_output("commit-tree", tree, "-m", "Initialize versioned docs")
    _run(["git", "update-ref", f"refs/heads/{branch}", commit])


def _deploy(
    config: Path,
    branch: str,
    remote: str,
    version: str,
    title: str,
) -> None:
    _run(
        [
            *MIKE_COMMAND,
            "deploy",
            "--config-file",
            str(config),
            "--branch",
            branch,
            "--remote",
            remote,
            "--ignore-remote-status",
            "--title",
            title,
            version,
        ]
    )


def publish(branch: str, remote: str, push: bool) -> list[ReleaseVersion]:
    """Build and publish all selected documentation versions."""
    if push and branch != "gh-pages":
        raise ValueError("Only the gh-pages branch can be pushed")

    releases = select_documented_releases(_git_output("tag", "--list").splitlines())
    if importlib.util.find_spec("mike") is None:
        raise RuntimeError("mike is not installed; install requirements-docs.txt")

    _reset_publish_branch(branch)

    with tempfile.TemporaryDirectory(prefix="hass-dmp-docs-") as temp:
        temp_root = Path(temp)
        for release in releases:
            config = prepare_release(
                release,
                temp_root / release.minor_version,
            )
            _deploy(
                config,
                branch,
                remote,
                release.minor_version,
                release.revision,
            )

    _deploy(
        REPO_ROOT / "zensical.toml",
        branch,
        remote,
        "latest",
        "Latest",
    )
    _run(
        [
            *MIKE_COMMAND,
            "set-default",
            "--config-file",
            str(REPO_ROOT / "zensical.toml"),
            "--branch",
            branch,
            "--remote",
            remote,
            "--ignore-remote-status",
            "latest",
        ]
    )

    if push:
        _run(["git", "push", "--force", remote, f"{branch}:{branch}"])

    return releases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="gh-pages")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--push", action="store_true")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List selected versions without building them.",
    )
    args = parser.parse_args()

    releases = select_documented_releases(_git_output("tag", "--list").splitlines())
    if args.list:
        for release in releases:
            print(f"{release.minor_version}\t{release.revision}\t{release.tag}")
        print("latest\tLatest\tmain")
        return

    published = publish(args.branch, args.remote, args.push)
    for release in published:
        print(f"Published {release.revision} at /{release.minor_version}/")
    print("Published main at /latest/ as Latest")


if __name__ == "__main__":
    main()
