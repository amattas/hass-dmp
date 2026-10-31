"""SemVer selection and historical documentation source preparation.

Canonical copy: the same script lives in every repository that publishes
versioned docs. Only the "Repository configuration" block differs.

Published versions:
  dev          the current checkout (main)
  <major.minor> the newest documented patch tag of every minor line, aliased
               by that tag so older full-version URLs keep resolving
  latest       alias of the highest stable release; the site default
               (falls back to dev while no release is tagged)
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

# --- Repository configuration ------------------------------------------------
PROJECT_NAME = "DMP for Home Assistant"
REPOSITORY = "amattas/hass-dmp"
# Trees a tag's docs build reads besides docs/ (e.g. Python sources that
# mkdocstrings or pydoc-markdown document). Missing paths are skipped.
SOURCE_PATHS: tuple[str, ...] = ()
# Generated, gitignored API reference: pydoc-markdown arguments (run from the
# repository root) and the docs-relative output page, or None.
API_REFERENCE_ARGS: tuple[str, ...] | None = None
API_REFERENCE_PAGE = "api/reference.md"
# -----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_OWNER, REPO_NAME = REPOSITORY.split("/")
SITE_URL = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/"
DEV_VERSION = "dev"
MIKE_TOML_BLOCK = '[project.extra.version]\nprovider = "mike"\ndefault = "latest"\n'
LATEST_ALIAS = "latest"
SEMVER_TAG = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$",
)

# Documentation sources a tag may carry: the Zensical site, a legacy MkDocs
# site, or a legacy Docusaurus site under website/.
DOC_SOURCES = (
    "zensical.toml",
    "mkdocs.yml",
    "website/docs/index.md",
    "website/docs/index.mdx",
)


@dataclass(frozen=True)
class ReleaseVersion:
    """A stable SemVer tag selected for documentation publication."""

    tag: str
    major: int
    minor: int
    patch: int

    @property
    def minor_version(self) -> str:
        """Return the stable documentation path for the minor line."""
        return f"{self.major}.{self.minor}"

    @property
    def revision(self) -> str:
        """Return the normalized full SemVer revision."""
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Deployment:
    """One mike version to publish; ``release`` is None for the checkout."""

    version: str
    title: str
    aliases: tuple[str, ...] = ()
    release: ReleaseVersion | None = None


def parse_semver_tag(tag: str) -> ReleaseVersion | None:
    """Parse a stable SemVer tag with an optional ``v`` prefix."""
    match = SEMVER_TAG.fullmatch(tag)
    if not match:
        return None

    return ReleaseVersion(
        tag=tag,
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
    )


def parse_release_tags(tags: Sequence[str]) -> list[ReleaseVersion]:
    """Parse every stable SemVer tag, rejecting ``vX.Y.Z``/``X.Y.Z`` duplicates."""
    releases: dict[str, ReleaseVersion] = {}

    for tag in tags:
        release = parse_semver_tag(tag)
        if release is None:
            continue

        existing = releases.get(release.revision)
        if existing is not None and existing.tag != release.tag:
            message = "Multiple tags normalize to the same SemVer revision"
            tags_found = ", ".join(sorted((existing.tag, release.tag)))
            raise ValueError(f"{message}: {tags_found}")
        releases[release.revision] = release

    return list(releases.values())


def _highest_patches(releases: Sequence[ReleaseVersion]) -> list[ReleaseVersion]:
    selected: dict[tuple[int, int], ReleaseVersion] = {}
    for release in releases:
        key = (release.major, release.minor)
        current = selected.get(key)
        if current is None or release.patch > current.patch:
            selected[key] = release
    return [selected[key] for key in sorted(selected)]


def select_latest_revisions(tags: Sequence[str]) -> list[ReleaseVersion]:
    """Select the highest patch revision for every major/minor line."""
    return _highest_patches(parse_release_tags(tags))


def has_documentation(tag: str) -> bool:
    """Return whether a tag carries a publishable documentation source."""
    return any(_git_path_exists(tag, path) for path in DOC_SOURCES)


def select_documented_releases(tags: Sequence[str]) -> list[ReleaseVersion]:
    """Select the highest documented patch revision for every minor line."""
    releases = parse_release_tags(tags)
    return _highest_patches([r for r in releases if has_documentation(r.tag)])


def plan_deployments(releases: Sequence[ReleaseVersion]) -> list[Deployment]:
    """Plan release lines oldest first, ``latest`` on the highest, then dev.

    Each line is aliased by its selected tag (``1.1.0``, ``v1.0.0``) so URLs
    from the earlier full-version scheme keep resolving. A SemVer tag cannot
    equal a ``major.minor`` version, ``dev`` or ``latest``.
    """
    ordered = sorted(releases, key=lambda release: (release.major, release.minor))
    plan = [
        Deployment(r.minor_version, r.revision, aliases=(r.tag,), release=r)
        for r in ordered
    ]
    if plan:
        plan[-1] = replace(plan[-1], aliases=(*plan[-1].aliases, LATEST_ALIAS))
    plan.append(Deployment(DEV_VERSION, DEV_VERSION))
    return plan


def default_version(plan: Sequence[Deployment]) -> str:
    """Return the site default: ``latest`` once a release exists, else dev."""
    if any(LATEST_ALIAS in deployment.aliases for deployment in plan):
        return LATEST_ALIAS
    return DEV_VERSION


def generate_api_reference(root: Path) -> Path | None:
    """Generate the API reference page under ``root`` when configured."""
    if API_REFERENCE_ARGS is None:
        return None

    reference = subprocess.run(
        [sys.executable, "-m", "pydoc_markdown.main", *API_REFERENCE_ARGS],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
    target = root / "docs" / API_REFERENCE_PAGE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\ntitle: API Reference\n---\n\n" + reference,
        encoding="utf-8",
    )
    return target


def _git_path_exists(tag: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{tag}:{path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _git_files(tag: str, prefix: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", tag, "--", prefix],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _git_file(tag: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{tag}:{path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def _export_tree(tag: str, prefix: str, destination: Path) -> list[Path]:
    exported: list[Path] = []
    prefix_path = Path(prefix)

    for source in _git_files(tag, prefix):
        relative = Path(source).relative_to(prefix_path)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_git_file(tag, source))
        exported.append(relative)

    if not exported:
        raise ValueError(f"Tag {tag} has no documentation under {prefix}")

    return exported


def _export_sources(tag: str, destination: Path) -> None:
    for path in SOURCE_PATHS:
        if _git_path_exists(tag, path):
            _export_tree(tag, path, destination / path)


def versioned_toml(config: str) -> str:
    """Enable the Zensical mike provider in a historical TOML config."""
    if "[project.extra.version]" in config:
        return config

    return config.rstrip() + "\n\n" + MIKE_TOML_BLOCK


def versioned_mkdocs(config: str) -> str:
    """Enable the Zensical mike provider in a historical MkDocs config."""
    if re.search(r"^\s+provider\s*:\s*mike\s*$", config, re.MULTILINE):
        return config
    if re.search(r"^extra\s*:", config, re.MULTILINE):
        raise ValueError("Legacy mkdocs.yml already defines an unsupported extra block")

    additions = [""]
    if not re.search(r"^site_url\s*:", config, re.MULTILINE):
        additions.append(f"site_url: {SITE_URL}")
    additions.extend(
        [
            "extra:",
            "  version:",
            "    provider: mike",
            "    default: latest",
            "",
        ]
    )
    return config.rstrip() + "\n" + "\n".join(additions)


def _display_name(path: Path) -> str:
    if path.as_posix() == API_REFERENCE_PAGE:
        return "API Reference"
    return path.stem.replace("-", " ").replace("_", " ").title()


def _legacy_index(release: ReleaseVersion, files: Sequence[Path]) -> str:
    """Build an archive landing page linking every exported Markdown page.

    The legacy Docusaurus index is MDX (JSX imports and components), so it is
    replaced by this generated page rather than exported as-is.
    """
    index = Path("index.md")
    pages = sorted(path for path in files if path.suffix == ".md" and path != index)
    links = [f"- [{_display_name(path)}]({path.as_posix()})" for path in pages]

    return "\n".join(
        [
            f"# {PROJECT_NAME} {release.revision}",
            "",
            f"This archived documentation reflects source tag `{release.tag}`.",
            "Features and setup steps may differ from **Latest**.",
            "",
            "## Documentation",
            "",
            *links,
            "",
        ]
    )


def _legacy_zensical_config(release: ReleaseVersion) -> str:
    return f"""[project]
site_name = "{PROJECT_NAME} {release.revision}"
site_description = "Archived documentation for {PROJECT_NAME} {release.revision}."
site_url = "{SITE_URL}"
docs_dir = "docs"
site_dir = "site"
repo_url = "https://github.com/{REPOSITORY}"
repo_name = "{REPOSITORY}"

[project.theme]
language = "en"
features = [
  "content.code.copy",
  "navigation.indexes",
  "navigation.top",
  "search.highlight",
]

[project.extra.version]
provider = "mike"
default = "latest"

[project.markdown_extensions.admonition]
[project.markdown_extensions.attr_list]
[project.markdown_extensions.tables]
[project.markdown_extensions.pymdownx.superfences]
custom_fences = [
  {{ name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" }},
]
"""


def prepare_release(release: ReleaseVersion, destination: Path) -> Path:
    """Export a tag's own documentation and return its build config."""
    docs_dir = destination / "docs"
    docs_dir.mkdir(parents=True)

    if _git_path_exists(release.tag, "zensical.toml"):
        _export_tree(release.tag, "docs", docs_dir)
        _export_sources(release.tag, destination)
        generate_api_reference(destination)
        config = _git_file(release.tag, "zensical.toml").decode("utf-8")
        config_path = destination / "zensical.toml"
        config_path.write_text(versioned_toml(config), encoding="utf-8")
        return config_path

    if _git_path_exists(release.tag, "mkdocs.yml"):
        _export_tree(release.tag, "docs", docs_dir)
        _export_sources(release.tag, destination)
        config = _git_file(release.tag, "mkdocs.yml").decode("utf-8")
        config_path = destination / "mkdocs.yml"
        config_path.write_text(versioned_mkdocs(config), encoding="utf-8")
        return config_path

    if _git_path_exists(release.tag, "website/docs/index.md") or _git_path_exists(
        release.tag, "website/docs/index.mdx"
    ):
        _export_tree(release.tag, "website/docs", docs_dir)
        for legacy in [*docs_dir.rglob("_category_.json"), *docs_dir.rglob("*.mdx")]:
            legacy.unlink()
        if API_REFERENCE_ARGS is not None:
            # Legacy pages link ../api/reference.md; the index then lists it.
            _export_sources(release.tag, destination)
            generate_api_reference(destination)
        markdown_files = [path.relative_to(docs_dir) for path in docs_dir.rglob("*.md")]
        (docs_dir / "index.md").write_text(
            _legacy_index(release, markdown_files),
            encoding="utf-8",
        )
        config_path = destination / "zensical.toml"
        config_path.write_text(
            _legacy_zensical_config(release),
            encoding="utf-8",
        )
        return config_path

    raise ValueError(f"Tag {release.tag} has no supported documentation source")
