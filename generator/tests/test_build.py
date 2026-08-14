import json
from pathlib import Path

import pytest

from fontpkg import family_from_metadata, select_file
from fontpkg_generator.build import SourceInfo, UnsupportedLicense, build_package


def test_build_static_package_tree(static_family_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    source = SourceInfo(repo="https://github.com/google/fonts", path="ofl/testface", commit="abc123")
    pkg_root = build_package(static_family_dir, out, source=source)

    assert pkg_root == out / "fontpkg-testface"
    module_dir = pkg_root / "src" / "fontpkg_testface"
    assert (module_dir / "files" / "Testface-Regular.ttf").is_file()
    assert (module_dir / "files" / "Testface-Italic.ttf").is_file()
    assert (module_dir / "LICENSE").is_file()
    assert (pkg_root / "LICENSE").is_file()

    meta = json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
    assert meta["family"] == "Testface"
    assert meta["slug"] == "testface"
    assert meta["version"] == "2.137"
    assert meta["license"] == "OFL-1.1"
    assert meta["source"]["commit"] == "abc123"
    assert {f["style"] for f in meta["files"]} == {"normal", "italic"}

    pyproject = (pkg_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "fontpkg-testface"' in pyproject
    assert 'version = "2.137"' in pyproject
    assert 'license = "OFL-1.1"' in pyproject
    assert 'dependencies = ["fontpkg>=0.1.0"]' in pyproject
    assert '[project.entry-points."fontpkg.family"]' in pyproject
    assert 'testface = "fontpkg_testface"' in pyproject


def test_post_release_versioning(static_family_dir: Path, tmp_path: Path) -> None:
    pkg_root = build_package(static_family_dir, tmp_path / "out", post=1)
    pyproject = (pkg_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "2.137.post1"' in pyproject
    meta = json.loads(
        (pkg_root / "src" / "fontpkg_testface" / "metadata.json").read_text(encoding="utf-8")
    )
    assert meta["version"] == "2.137"


def test_build_variable_package_metadata(variable_family_dir: Path, tmp_path: Path) -> None:
    pkg_root = build_package(variable_family_dir, tmp_path / "out")
    meta = json.loads(
        (pkg_root / "src" / "fontpkg_varface" / "metadata.json").read_text(encoding="utf-8")
    )
    assert meta["version"] == "1.002"
    (entry,) = meta["files"]
    assert entry["variable"] is True
    assert entry["weight"] is None
    assert meta["axes"] == [{"tag": "wght", "min": 100.0, "max": 900.0}]


def test_roundtrip_with_core_resolver(variable_family_dir: Path, tmp_path: Path) -> None:
    pkg_root = build_package(variable_family_dir, tmp_path / "out")
    module_dir = pkg_root / "src" / "fontpkg_varface"
    meta = json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
    fam = family_from_metadata(meta, module_dir)
    chosen = select_file(fam, 550, "normal")
    assert chosen.variable
    assert Path(chosen.path).is_file()


def test_unsupported_license_is_rejected(static_family_dir: Path, tmp_path: Path) -> None:
    metadata = (static_family_dir / "METADATA.pb").read_text(encoding="utf-8")
    (static_family_dir / "METADATA.pb").write_text(
        metadata.replace('license: "OFL"', 'license: "UFL"'), encoding="utf-8"
    )
    with pytest.raises(UnsupportedLicense):
        build_package(static_family_dir, tmp_path / "out")


def test_missing_license_file_is_rejected(static_family_dir: Path, tmp_path: Path) -> None:
    (static_family_dir / "OFL.txt").unlink()
    with pytest.raises(FileNotFoundError):
        build_package(static_family_dir, tmp_path / "out")
