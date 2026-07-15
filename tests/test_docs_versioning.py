"""Tests for the versioned-docs selection logic in scripts/docs_versioning.py."""

from pathlib import Path

import pytest

from scripts.docs_versioning import (
    _legacy_index,
    parse_semver_tag,
    select_documented_releases,
    select_latest_revisions,
)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # The repo's real tag shape: prereleases and the highest patch per
        # minor line; both v-prefixed and bare tags parse.
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
            [("0.4", "0.4.0"), ("0.5", "0.5.5"), ("1.0", "1.0.1")],
        ),
        ([], []),
        (["not-a-version", "v1.0.0-rc1"], []),
    ],
)
def test_select_latest_revisions(tags, expected):
    releases = select_latest_revisions(tags)
    assert [(r.minor_version, r.revision) for r in releases] == expected


def test_select_documented_releases_skips_tags_without_docs(monkeypatch):
    # Only the 1.0 line has a docs site in its tag; 0.4/0.5 must be skipped,
    # not fail the publish.
    monkeypatch.setattr(
        "scripts.docs_versioning._git_path_exists",
        lambda tag, path: tag == "1.0.1" and path == "website/docs/index.md",
    )
    releases = select_documented_releases(
        ["v0.4.0", "v0.5.5", "1.0.1"]
    )
    assert [r.tag for r in releases] == ["1.0.1"]


def test_legacy_index_links_every_page_except_the_replaced_index():
    release = parse_semver_tag("1.0.1")
    index = _legacy_index(
        release,
        [
            Path("index.md"),
            Path("guide/installation.md"),
            Path("guide/panel-configuration.md"),
            Path("guide/features.md"),
        ],
    )
    assert "(guide/installation.md)" in index
    assert "(guide/panel-configuration.md)" in index
    assert "(guide/features.md)" in index
    assert "(index.md)" not in index
    assert "1.0.1" in index
