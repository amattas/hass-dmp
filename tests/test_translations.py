"""Consistency checks for strings.json, translations and icons.json."""

import json
from pathlib import Path

from custom_components.dmp.sensor import STATUS_OPTIONS

COMPONENT = Path(__file__).parent.parent / "custom_components" / "dmp"


def _load(name: str) -> dict:
    return json.loads((COMPONENT / name).read_text(encoding="utf-8"))


def test_english_translation_matches_strings():
    """translations/en.json mirrors strings.json."""
    assert _load("translations/en.json") == _load("strings.json")


def test_every_status_option_has_a_label_and_icon():
    """The status enum's options are all translated and all have an icon."""
    options = set(STATUS_OPTIONS)
    labels = _load("strings.json")["entity"]["sensor"]["status"]["state"]
    icons = _load("icons.json")["entity"]["sensor"]["status"]["state"]
    assert labels.keys() == options
    assert icons.keys() == options
