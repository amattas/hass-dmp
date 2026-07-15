"""SemVer selection and historical documentation source preparation."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_TAG = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)$"
)
SITE_URL = "https://amattas.github.io/hass-dmp/"

# Documentation sources a tag may carry, newest layout first: the root
# Zensical site, or the legacy Docusaurus site under website/.
DOC_SOURCES = ("zensical.toml", "website/docs/index.md")


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


def select_latest_revisions(tags: Sequence[str]) -> list[ReleaseVersion]:
    """Select the highest patch revision for every major/minor line."""
    selected: dict[tuple[int, int], ReleaseVersion] = {}

    for tag in tags:
        release = parse_semver_tag(tag)
        if release is None:
            continue

        key = (release.major, release.minor)
        current = selected.get(key)
        if current is None or release.patch > current.patch:
            selected[key] = release
            continue

        if release.patch == current.patch and release.tag != current.tag:
            raise ValueError(
                "Multiple tags normalize to the same SemVer revision: "
                f"{current.tag}, {release.tag}"
            )

    return [selected[key] for key in sorted(selected)]


def has_documentation(tag: str) -> bool:
    """Return whether a tag carries a publishable documentation source."""
    return any(_git_path_exists(tag, path) for path in DOC_SOURCES)


def select_documented_releases(tags: Sequence[str]) -> list[ReleaseVersion]:
    """Select publishable releases, skipping tags without documentation."""
    return [
        release
        for release in select_latest_revisions(tags)
        if has_documentation(release.tag)
    ]


def _git_path_exists(tag: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{tag}:{path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _git_files(tag: str, prefix: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", tag, "--", prefix],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


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


def versioned_toml(config: str) -> str:
    """Enable the Zensical mike provider in a historical TOML config."""
    if "[project.extra.version]" in config:
        return config

    return (
        config.rstrip()
        + "\n\n[project.extra.version]\n"
        + 'provider = "mike"\n'
        + 'default = "latest"\n'
    )


def _display_name(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _legacy_index(release: ReleaseVersion, files: Sequence[Path]) -> str:
    """Build an archive landing page linking every exported Markdown page.

    The legacy Docusaurus index.md is MDX (JSX imports and components), so it
    is replaced by this generated page rather than exported as-is.
    """
    pages = sorted(
        path
        for path in files
        if path.suffix == ".md" and path != Path("index.md")
    )
    links = [f"- [{_display_name(path)}]({path.as_posix()})" for path in pages]

    return "\n".join(
        [
            f"# DMP for Home Assistant {release.revision}",
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
site_name = "DMP for Home Assistant {release.revision}"
site_description = "Archived documentation for DMP for Home Assistant {release.revision}."
site_url = "{SITE_URL}"
docs_dir = "docs"
site_dir = "site"
repo_url = "https://github.com/amattas/hass-dmp"
repo_name = "amattas/hass-dmp"

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
        config = _git_file(release.tag, "zensical.toml").decode("utf-8")
        config_path = destination / "zensical.toml"
        config_path.write_text(versioned_toml(config), encoding="utf-8")
        return config_path

    if _git_path_exists(release.tag, "website/docs/index.md"):
        files = _export_tree(release.tag, "website/docs", docs_dir)
        for category in docs_dir.rglob("_category_.json"):
            category.unlink()
        markdown_files = [path for path in files if path.suffix == ".md"]
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
