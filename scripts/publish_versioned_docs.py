"""Publish versioned documentation (mike) to the gh-pages branch.

Canonical copy: the same script lives in every repository that publishes
versioned docs; repository specifics live in docs_versioning.py.

The publication branch is rebuilt from scratch on every run:
  dev          from the current checkout (main)
  <major.minor> from the newest documented patch tag of each minor line,
               aliased by that tag (e.g. 1.1.0) so full-version URLs resolve
  latest       alias of the highest stable release and the site default
               (dev is the default while no release is tagged)
"""

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

from docs_versioning import (
    REPO_NAME,
    Deployment,
    default_version,
    generate_api_reference,
    plan_deployments,
    prepare_release,
    select_documented_releases,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_CONFIG = REPO_ROOT / "zensical.toml"
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
    paths = [path for path in script_paths if path] + [environment.get("PATH", "")]
    environment["PATH"] = os.pathsep.join(paths)
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


def _plan() -> list[Deployment]:
    tags = _git_output("tag", "--list").splitlines()
    return plan_deployments(select_documented_releases(tags))


def _reset_publish_branch(branch: str) -> None:
    if branch != "gh-pages" and not branch.startswith("docs-version-"):
        raise ValueError("Publication branch must be gh-pages or docs-version-*")

    current_branch = _git_output("branch", "--show-current")
    if current_branch == branch:
        raise ValueError(f"Cannot replace the checked-out branch: {branch}")

    tree = _run(["git", "mktree"], input_text="", capture_output=True).stdout.strip()
    commit = _git_output("commit-tree", tree, "-m", "Initialize versioned docs")
    _run(["git", "update-ref", f"refs/heads/{branch}", commit])


def _mike(subcommand: str, config: Path, branch: str, remote: str, *args: str) -> None:
    _run(
        [
            *MIKE_COMMAND,
            subcommand,
            "--config-file",
            str(config),
            "--branch",
            branch,
            "--remote",
            remote,
            "--ignore-remote-status",
            *args,
        ]
    )


def publish(branch: str, remote: str, push: bool) -> list[Deployment]:
    """Build every planned documentation version onto ``branch``."""
    if push and branch != "gh-pages":
        raise ValueError("Only the gh-pages branch can be pushed")

    plan = _plan()
    if importlib.util.find_spec("mike") is None:
        raise RuntimeError("mike is not installed; install the docs requirements")

    _reset_publish_branch(branch)
    generate_api_reference(REPO_ROOT)

    with tempfile.TemporaryDirectory(prefix=f"{REPO_NAME}-docs-") as temp:
        temp_root = Path(temp)
        for deployment in plan:
            config = (
                CURRENT_CONFIG
                if deployment.release is None
                else prepare_release(deployment.release, temp_root / deployment.version)
            )
            update_aliases = ("--update-aliases",) if deployment.aliases else ()
            _mike(
                "deploy",
                config,
                branch,
                remote,
                *update_aliases,
                "--title",
                deployment.title,
                deployment.version,
                *deployment.aliases,
            )

    _mike("set-default", CURRENT_CONFIG, branch, remote, default_version(plan))

    if push:
        _run(["git", "push", "--force", remote, f"{branch}:{branch}"])

    return plan


def _describe(deployment: Deployment) -> str:
    source = "main" if deployment.release is None else deployment.release.tag
    aliases = ",".join(deployment.aliases) or "-"
    return f"{deployment.version}\t{deployment.title}\t{source}\t{aliases}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="gh-pages")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--push", action="store_true")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List planned versions (version, title, source, aliases) without building.",
    )
    args = parser.parse_args()

    plan = _plan() if args.list else publish(args.branch, args.remote, args.push)
    for deployment in plan:
        print(_describe(deployment))
    print(f"default\t{default_version(plan)}")


if __name__ == "__main__":
    main()
