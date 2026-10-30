"""Contract tests for versioned documentation publication.

Canonical copy: the same file lives in every repository that publishes
versioned docs with scripts/publish_versioned_docs.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import docs_versioning
import publish_versioned_docs

MKDOCS_WITH_MIKE = "site_url: https://x/\nextra:\n  version:\n    provider: mike\n"


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (
            [
                "1.0.1",
                "v0.4.0",
                "v0.5.0",
                "v0.5.3",
                "v0.5.5",
                "v1.0.0",
                "v1.0.0-alpha1",
                "v1.0.0-beta3",
            ],
            [
                ("0.4", "0.4.0", "v0.4.0"),
                ("0.5", "0.5.5", "v0.5.5"),
                ("1.0", "1.0.1", "1.0.1"),
            ],
        ),
        (
            ["bulk", "v0.0.1", "v0.0.2", "0.3.0", "0.3.3", "1.2.0-rc.1", "1.2.4"],
            [
                ("0.0", "0.0.2", "v0.0.2"),
                ("0.3", "0.3.3", "0.3.3"),
                ("1.2", "1.2.4", "1.2.4"),
            ],
        ),
        ([], []),
        (["not-a-version", "v1.0.0-rc1"], []),
    ],
)
def test_selects_highest_patch_for_each_minor_version(
    tags: list[str],
    expected: list[tuple[str, str, str]],
) -> None:
    releases = docs_versioning.select_latest_revisions(tags)

    assert [(r.minor_version, r.revision, r.tag) for r in releases] == expected


@pytest.mark.parametrize(
    "tags",
    [
        ["v1.2.3", "1.2.3"],
        # Fatal whatever the order, also below the selected patch.
        ["1.0.0", "v1.0.0", "1.0.1"],
        ["1.0.0", "1.0.1", "v1.0.0"],
    ],
)
def test_rejects_duplicate_normalized_semver_tags(
    monkeypatch: pytest.MonkeyPatch,
    tags: list[str],
) -> None:
    # Duplicates are fatal even among tags without documentation.
    monkeypatch.setattr(docs_versioning, "_git_path_exists", lambda tag, path: False)

    with pytest.raises(ValueError, match="same SemVer revision"):
        docs_versioning.select_latest_revisions(tags)
    with pytest.raises(ValueError, match="same SemVer revision"):
        docs_versioning.select_documented_releases(tags)


def test_selects_highest_documented_patch_and_skips_undocumented_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documented = {"1.0.0", "1.1.0"}

    def git_path_exists(tag: str, path: str) -> bool:
        return tag in documented and path == "website/docs/index.md"

    monkeypatch.setattr(docs_versioning, "_git_path_exists", git_path_exists)

    tags = ["v0.4.0", "v0.5.5", "1.0.0", "1.0.1", "1.1.0"]
    releases = docs_versioning.select_documented_releases(tags)

    # 1.0.1 has no docs, so the 1.0 line falls back to 1.0.0.
    assert [r.tag for r in releases] == ["1.0.0", "1.1.0"]


@pytest.mark.parametrize(
    ("tags", "expected_plan", "expected_default"),
    [
        (
            ["1.1.0", "v0.5.5", "1.0.1", "1.2.0-beta1"],
            # The selected tag stays an alias so old full-version URLs resolve.
            [
                ("0.5", "0.5.5", ("v0.5.5",)),
                ("1.0", "1.0.1", ("1.0.1",)),
                ("1.1", "1.1.0", ("1.1.0", "latest")),
                ("dev", "dev", ()),
            ],
            "latest",
        ),
        ([], [("dev", "dev", ())], "dev"),
    ],
)
def test_plans_dev_from_main_and_latest_on_highest_stable_release(
    tags: list[str],
    expected_plan: list[tuple[str, str, tuple[str, ...]]],
    expected_default: str,
) -> None:
    releases = docs_versioning.select_latest_revisions(tags)
    plan = docs_versioning.plan_deployments(releases)

    assert [(d.version, d.title, d.aliases) for d in plan] == expected_plan
    aliases = [alias for d in plan for alias in d.aliases]
    assert len(aliases) == len(set(aliases))
    assert not set(aliases) & {d.version for d in plan}
    # dev is built from the current checkout (main), not from a tag.
    assert plan[-1].release is None
    assert docs_versioning.default_version(plan) == expected_default


def test_versioned_toml_enables_mike_with_latest_default() -> None:
    toml = docs_versioning.versioned_toml("[project]\nsite_name = 'Demo'\n")

    assert '[project.extra.version]\nprovider = "mike"' in toml
    assert 'default = "latest"' in toml
    assert docs_versioning.versioned_toml(toml) == toml


@pytest.mark.parametrize(
    ("config", "expected_lines"),
    [
        (
            "site_name: Demo\n",
            [
                f"site_url: {docs_versioning.SITE_URL}",
                "provider: mike",
                "default: latest",
            ],
        ),
        # Legacy MkDocs configs that already enable mike are used as-is.
        (MKDOCS_WITH_MIKE, ["site_url: https://x/", "provider: mike"]),
    ],
)
def test_versioned_mkdocs_enables_mike(
    config: str,
    expected_lines: list[str],
) -> None:
    versioned = docs_versioning.versioned_mkdocs(config)

    for line in expected_lines:
        assert line in versioned
    assert versioned.count("site_url:") == 1
    assert versioned.count("extra:") == 1


@pytest.mark.parametrize(
    "api_reference_args",
    [("-I", "src", "-p", "demo"), None],
)
def test_prepares_legacy_docusaurus_release_with_optional_api_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    api_reference_args: tuple[str, ...] | None,
) -> None:
    tree = {
        "website/docs/index.mdx": b"import X from 'y';\n",
        "website/docs/features.md": b"# Features\n",
        "website/docs/guide/installation.md": b"[API](../api/reference.md)\n",
        "website/docs/guide/_category_.json": b"{}",
        "src/demo/__init__.py": b"",
    }

    def git_path_exists(tag: str, path: str) -> bool:
        return any(name == path or name.startswith(f"{path}/") for name in tree)

    def git_files(tag: str, prefix: str) -> list[str]:
        return [name for name in tree if name.startswith(f"{prefix}/")]

    def generate_api_reference(root: Path) -> Path:
        assert (root / "src" / "demo" / "__init__.py").exists()
        target = root / "docs" / docs_versioning.API_REFERENCE_PAGE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# API\n", encoding="utf-8")
        return target

    monkeypatch.setattr(docs_versioning, "API_REFERENCE_ARGS", api_reference_args)
    monkeypatch.setattr(docs_versioning, "SOURCE_PATHS", ("src",))
    monkeypatch.setattr(docs_versioning, "_git_path_exists", git_path_exists)
    monkeypatch.setattr(docs_versioning, "_git_files", git_files)
    monkeypatch.setattr(docs_versioning, "_git_file", lambda tag, path: tree[path])
    monkeypatch.setattr(
        docs_versioning, "generate_api_reference", generate_api_reference
    )
    release = docs_versioning.parse_semver_tag("1.0.1")
    assert release is not None

    config = docs_versioning.prepare_release(release, tmp_path)

    index = (tmp_path / "docs" / "index.md").read_text(encoding="utf-8")
    assert config == tmp_path / "zensical.toml"
    assert "(guide/installation.md)" in index
    assert "(features.md)" in index
    assert "(index.md)" not in index
    assert "1.0.1" in index
    assert not list((tmp_path / "docs").rglob("_category_.json"))
    generated = api_reference_args is not None
    assert (tmp_path / "docs" / "api" / "reference.md").exists() == generated
    assert (tmp_path / "src").exists() == generated
    if generated:
        assert "- [API Reference](api/reference.md)" in index
    else:
        assert "api/reference.md" not in index


def test_publish_deploys_release_aliases_with_alias_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = docs_versioning.plan_deployments(
        docs_versioning.select_latest_revisions(["1.0.1", "1.1.0"])
    )
    calls: list[tuple[str, ...]] = []

    def mike(
        subcommand: str, config: Path, branch: str, remote: str, *args: str
    ) -> None:
        calls.append((subcommand, *args))

    monkeypatch.setattr(publish_versioned_docs, "_plan", lambda: plan)
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: True)
    monkeypatch.setattr(publish_versioned_docs, "_reset_publish_branch", lambda _: None)
    monkeypatch.setattr(
        publish_versioned_docs, "generate_api_reference", lambda _: None
    )
    monkeypatch.setattr(
        publish_versioned_docs, "prepare_release", lambda release, path: path / "z.toml"
    )
    monkeypatch.setattr(publish_versioned_docs, "_mike", mike)

    publish_versioned_docs.publish("docs-version-test", "origin", push=False)

    # --update-aliases lets a rerun move an existing alias instead of failing.
    assert calls == [
        ("deploy", "--update-aliases", "--title", "1.0.1", "1.0", "1.0.1"),
        ("deploy", "--update-aliases", "--title", "1.1.0", "1.1", "1.1.0", "latest"),
        ("deploy", "--title", "dev", "dev"),
        ("set-default", "latest"),
    ]


def test_rejects_pushing_a_preview_branch() -> None:
    with pytest.raises(ValueError, match="Only the gh-pages branch"):
        publish_versioned_docs.publish("docs-version-preview", "origin", push=True)


def test_docs_workflow_calls_the_shared_publisher() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "docs.yml"
    text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["docs"]

    # PyYAML reads the bare `on:` key as boolean True.
    triggers = workflow[True]
    assert set(triggers) == {"push", "workflow_dispatch", "workflow_call"}
    assert triggers["push"] == {"branches": ["main"]}
    assert workflow["permissions"] == {"contents": "read"}
    # The shared workflow checks out main with full history and runs this repo's
    # scripts/publish_versioned_docs.py --push under the docs-gh-pages concurrency group.
    assert job["uses"] == "mattas-net/.github/.github/workflows/docs.yml@main"
    assert job["permissions"] == {"contents": "write"}
    assert job["with"]["version"] == "${{ inputs.version }}"
    assert (REPO_ROOT / "scripts" / "publish_versioned_docs.py").is_file()
    # gh-pages is served directly; no Pages artifact/deployment pipeline.
    retired = ("configure-pages", "upload-pages-artifact", "deploy-pages")
    for action in (*retired, "github-pages"):
        assert action not in text
    assert "private repos build gh-pages and keep Pages disabled" in text
