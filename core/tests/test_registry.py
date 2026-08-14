import importlib
import json
import sys
import types
from pathlib import Path

import pytest

import fontpkg
import fontpkg._registry as registry
from fontpkg import FamilyNotInstalled


def make_family_package(root: Path, module_name: str, family: str, slug: str) -> types.ModuleType:
    pkg_dir = root / module_name
    files_dir = pkg_dir / "files"
    files_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text(f'FAMILY = "{family}"\n', encoding="utf-8")
    (files_dir / "Regular.ttf").write_bytes(b"\x00")
    metadata = {
        "schema": 1,
        "family": family,
        "slug": slug,
        "version": "1.234",
        "license": "OFL-1.1",
        "axes": [],
        "files": [
            {"path": "files/Regular.ttf", "style": "normal", "weight": 400, "variable": False}
        ],
    }
    (pkg_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module(module_name)
    finally:
        sys.path.remove(str(root))


class FakeEntryPoint:
    def __init__(self, name: str, module: types.ModuleType) -> None:
        self.name = name
        self._module = module

    def load(self) -> types.ModuleType:
        return self._module


@pytest.fixture
def fake_registry(tmp_path, monkeypatch):
    module = make_family_package(tmp_path, "fontpkg_testface", "Testface", "testface")

    def fake_entry_points(group: str):
        if group == registry.ENTRY_POINT_GROUP:
            return [FakeEntryPoint("testface", module)]
        return []

    monkeypatch.setattr(registry, "entry_points", fake_entry_points)
    monkeypatch.setattr(registry, "_cache", None)
    yield module
    monkeypatch.setattr(registry, "_cache", None)


def test_families_discovers_entry_points(fake_registry) -> None:
    fams = fontpkg.families(refresh=True)
    assert list(fams) == ["testface"]
    assert fams["testface"].version == "1.234"


def test_family_lookup_is_slug_insensitive(fake_registry) -> None:
    fontpkg.refresh()
    assert fontpkg.family("Testface").name == "Testface"
    assert fontpkg.family("  TESTFACE ").slug == "testface"


def test_missing_family_error_names_install_command(fake_registry) -> None:
    fontpkg.refresh()
    with pytest.raises(FamilyNotInstalled, match="uv add fontpkg-open-sans"):
        fontpkg.family("Open Sans")


def test_path_returns_existing_file(fake_registry) -> None:
    fontpkg.refresh()
    p = fontpkg.path("Testface")
    assert p.name == "Regular.ttf"
    assert p.is_file()


def test_legacy_fonts_ttf_group(tmp_path, monkeypatch) -> None:
    legacy_file = tmp_path / "Legacy.ttf"
    legacy_file.write_bytes(b"\x00")

    class LegacyEP:
        name = "LegacyFace"

        @staticmethod
        def load() -> str:
            return str(legacy_file)

    def fake_entry_points(group: str):
        if group == registry.LEGACY_GROUP:
            return [LegacyEP()]
        return []

    monkeypatch.setattr(registry, "entry_points", fake_entry_points)
    monkeypatch.setattr(registry, "_cache", None)
    fams = fontpkg.families(refresh=True)
    assert fams["legacyface"].files[0].path == legacy_file
    monkeypatch.setattr(registry, "_cache", None)
