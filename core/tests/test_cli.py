from pathlib import Path

import pytest

import fontpkg._registry as registry
from fontpkg import Family, FontFile
from fontpkg.__main__ import main


@pytest.fixture
def one_family(ttf_factory, monkeypatch):
    ttf_path: Path = ttf_factory()
    fam = Family(
        name="Testface",
        slug="testface",
        version="1.0",
        license="OFL-1.1",
        files=(FontFile(ttf_path, "normal", 400, False),),
    )
    monkeypatch.setattr(registry, "_cache", {"testface": fam})
    yield fam
    monkeypatch.setattr(registry, "_cache", None)


def test_list_shows_family(one_family, capsys) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "testface" in out
    assert "OFL-1.1" in out


def test_default_command_is_list(one_family, capsys) -> None:
    assert main([]) == 0
    assert "testface" in capsys.readouterr().out


def test_path_command(one_family, capsys) -> None:
    assert main(["path", "Testface", "--weight", "bold", "--nearest"]) == 0
    assert capsys.readouterr().out.strip().endswith(".ttf")


def test_path_command_missing_family(one_family, capsys) -> None:
    assert main(["path", "Nope"]) == 1
    assert "uv add fontpkg-nope" in capsys.readouterr().err
