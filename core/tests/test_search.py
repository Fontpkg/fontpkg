import json
from pathlib import Path

import pytest

import fontpkg._registry as registry
from fontpkg.__main__ import main
from fontpkg._catalog import fetch_catalog, search_catalog

CATALOG = {
    "inter": {
        "family": "Inter",
        "slug": "inter",
        "package": "fontpkg-inter",
        "version": "4.001",
        "license": "OFL-1.1",
        "category": ["SANS_SERIF"],
        "styles": ["italic", "normal"],
        "variable": True,
        "weights": [],
        "weight_range": [100, 900],
    },
    "merriweather": {
        "family": "Merriweather",
        "slug": "merriweather",
        "package": "fontpkg-merriweather",
        "version": "2.100",
        "license": "OFL-1.1",
        "category": ["SERIF"],
        "styles": ["italic", "normal"],
        "variable": True,
        "weights": [],
        "weight_range": [300, 900],
    },
}


@pytest.fixture
def catalog_file(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    return path


def test_fetch_catalog_from_file(catalog_file: Path) -> None:
    catalog = fetch_catalog(str(catalog_file))
    assert set(catalog) == {"inter", "merriweather"}


def test_search_matches_slug_family_category() -> None:
    assert [e["slug"] for e in search_catalog(CATALOG, "inter")] == ["inter"]
    assert [e["slug"] for e in search_catalog(CATALOG, "Merri")] == ["merriweather"]
    assert [e["slug"] for e in search_catalog(CATALOG, "serif")] == ["inter", "merriweather"]
    assert search_catalog(CATALOG, "comic") == []


def test_search_no_query_returns_all_sorted() -> None:
    assert [e["slug"] for e in search_catalog(CATALOG, None)] == ["inter", "merriweather"]


def test_search_category_filter() -> None:
    assert [e["slug"] for e in search_catalog(CATALOG, None, category="sans")] == ["inter"]
    assert [e["slug"] for e in search_catalog(CATALOG, None, category="SANS SERIF")] == ["inter"]
    only_serif = search_catalog(CATALOG, None, category="serif")
    assert [e["slug"] for e in only_serif] == ["inter", "merriweather"]
    assert search_catalog(CATALOG, "merri", category="sans_serif") == []


def test_search_cli_output(catalog_file: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(registry, "_cache", {})
    assert main(["search", "serif", "--catalog-url", str(catalog_file)]) == 0
    out = capsys.readouterr().out
    assert "uv add fontpkg-inter" in out
    assert "wght 100-900" in out
    monkeypatch.setattr(registry, "_cache", None)


def test_search_cli_marks_installed(catalog_file: Path, capsys, monkeypatch) -> None:
    from fontpkg import Family, FontFile

    fam = Family("Inter", "inter", "4.001", "OFL-1.1", (FontFile(Path("x.ttf"), "normal", 400, False),))
    monkeypatch.setattr(registry, "_cache", {"inter": fam})
    assert main(["search", "inter", "--catalog-url", str(catalog_file)]) == 0
    assert "[installed]" in capsys.readouterr().out
    monkeypatch.setattr(registry, "_cache", None)


def test_search_cli_no_matches(catalog_file: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(registry, "_cache", {})
    assert main(["search", "zzz", "--catalog-url", str(catalog_file)]) == 0
    assert "no installable families" in capsys.readouterr().out
    monkeypatch.setattr(registry, "_cache", None)


def test_search_cli_bad_source(capsys, monkeypatch) -> None:
    assert main(["search", "x", "--catalog-url", "/nonexistent/catalog.json"]) == 1
    assert "could not fetch catalog" in capsys.readouterr().err
