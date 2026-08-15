import json
from pathlib import Path

from fontpkg_generator.build import build_package
from fontpkg_generator.site import build_site
from fontpkg_generator.sync import catalog_entry


def _prepare(family_dir: Path, tmp_path: Path) -> tuple[Path, Path]:
    packages = tmp_path / "pkgs"
    pkg_root = build_package(family_dir, packages)
    module_dir = next((pkg_root / "src").iterdir())
    meta = json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({meta["slug"]: catalog_entry(meta)}), encoding="utf-8")
    return catalog_path, packages


def test_static_site_output(static_family_dir: Path, tmp_path: Path) -> None:
    catalog_path, packages = _prepare(static_family_dir, tmp_path)
    out = build_site(catalog_path, packages, tmp_path / "site")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert (out / "fonts" / "testface-400-normal.ttf").is_file()
    assert (out / "fonts" / "testface-400-italic.ttf").is_file()
    assert (out / ".nojekyll").is_file()
    assert (out / "catalog.json").is_file()
    assert '"family": "Testface"' in html
    assert 'font-family: "Testface"' in html
    assert 'url("fonts/testface-400-normal.ttf") format("truetype")' in html
    assert "font-weight: 400" in html
    assert "__FAMILY_DATA__" not in html


def test_site_state_filter_hides_unpublished(static_family_dir: Path, tmp_path: Path) -> None:
    catalog_path, packages = _prepare(static_family_dir, tmp_path)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"testface": {"package": "fontpkg-testface", "published": False}}),
        encoding="utf-8",
    )
    out = build_site(catalog_path, packages, tmp_path / "site", state_path=state_path)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '"family": "Testface"' not in html

    state_path.write_text(
        json.dumps({"testface": {"package": "fontpkg-testface", "published": True}}),
        encoding="utf-8",
    )
    out = build_site(catalog_path, packages, tmp_path / "site2", state_path=state_path)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '"family": "Testface"' in html


def test_variable_site_font_faces(variable_family_dir: Path, tmp_path: Path) -> None:
    catalog_path, packages = _prepare(variable_family_dir, tmp_path)
    out = build_site(catalog_path, packages, tmp_path / "site")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert (out / "fonts" / "varface-normal.ttf").is_file()
    assert 'format("truetype-variations")' in html
    assert "font-weight: 100 900" in html
