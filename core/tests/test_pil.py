from pathlib import Path

import pytest

import fontpkg._registry as registry
from fontpkg import Family, FontFile

PIL = pytest.importorskip("PIL")


@pytest.fixture
def installed_ttf(ttf_factory, monkeypatch):
    ttf_path: Path = ttf_factory()
    fam = Family(
        name="Testface",
        slug="testface",
        version="1.0",
        license="OFL-1.1",
        files=(FontFile(ttf_path, "normal", 400, False),),
    )
    monkeypatch.setattr(registry, "_cache", {"testface": fam})
    yield ttf_path
    monkeypatch.setattr(registry, "_cache", None)


def test_truetype_loads_font(installed_ttf) -> None:
    from fontpkg.pil import truetype

    font = truetype("Testface", size=24)
    assert font.path == str(installed_ttf)
    assert font.size == 24


def test_truetype_weight_alias(installed_ttf) -> None:
    from fontpkg.pil import truetype

    font = truetype("Testface", size=12, weight="regular")
    assert font.size == 12
