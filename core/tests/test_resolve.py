from pathlib import Path

import pytest

from fontpkg import (
    Family,
    FontFile,
    StyleNotAvailable,
    WeightNotAvailable,
    normalize_style,
    normalize_weight,
    select_file,
    slugify,
)


def static_family() -> Family:
    return Family(
        name="Testface",
        slug="testface",
        version="1.0",
        license="OFL-1.1",
        files=(
            FontFile(Path("r400.ttf"), "normal", 400, False),
            FontFile(Path("r700.ttf"), "normal", 700, False),
            FontFile(Path("i400.ttf"), "italic", 400, False),
        ),
    )


def variable_family() -> Family:
    return Family(
        name="Varface",
        slug="varface",
        version="1.0",
        license="OFL-1.1",
        files=(
            FontFile(Path("vf.ttf"), "normal", None, True, wght_min=100, wght_max=900),
            FontFile(Path("vf-italic.ttf"), "italic", None, True, wght_min=100, wght_max=900),
        ),
    )


def test_slugify() -> None:
    assert slugify("Open Sans") == "open-sans"
    assert slugify("  Source_Sans 3 ") == "source-sans-3"


def test_normalize_weight_aliases() -> None:
    assert normalize_weight("bold") == 700
    assert normalize_weight("Semi-Bold") == 600
    assert normalize_weight(432) == 432


def test_normalize_weight_rejects_unknown() -> None:
    with pytest.raises(WeightNotAvailable):
        normalize_weight("chunky")
    with pytest.raises(WeightNotAvailable):
        normalize_weight(0)


def test_normalize_style() -> None:
    assert normalize_style("Italic") == "italic"
    assert normalize_style("oblique") == "italic"
    assert normalize_style("Regular") == "normal"


def test_exact_static_match() -> None:
    fam = static_family()
    assert select_file(fam, 700, "normal").path.name == "r700.ttf"
    assert select_file(fam, 400, "italic").path.name == "i400.ttf"


def test_missing_weight_raises_without_nearest() -> None:
    with pytest.raises(WeightNotAvailable, match="nearest=True"):
        select_file(static_family(), 500, "normal")


def test_nearest_picks_closest_and_prefers_lighter_tie() -> None:
    fam = static_family()
    assert select_file(fam, 500, "normal", nearest=True).path.name == "r400.ttf"
    assert select_file(fam, 651, "normal", nearest=True).path.name == "r700.ttf"


def test_missing_style_raises() -> None:
    fam = Family("X", "x", "1", "OFL-1.1", (FontFile(Path("r.ttf"), "normal", 400, False),))
    with pytest.raises(StyleNotAvailable):
        select_file(fam, 400, "italic")


def test_variable_covers_any_weight_in_range() -> None:
    fam = variable_family()
    assert select_file(fam, 137, "normal").path.name == "vf.ttf"
    assert select_file(fam, 850, "italic").path.name == "vf-italic.ttf"


def test_variable_out_of_range_raises() -> None:
    fam = Family(
        "N",
        "n",
        "1",
        "OFL-1.1",
        (FontFile(Path("vf.ttf"), "normal", None, True, wght_min=300, wght_max=700),),
    )
    with pytest.raises(WeightNotAvailable):
        select_file(fam, 100, "normal")
    assert select_file(fam, 100, "normal", nearest=True).path.name == "vf.ttf"


def test_family_properties() -> None:
    fam = static_family()
    assert fam.styles == ["italic", "normal"]
    assert fam.weights == [400, 700]
    assert fam.weight_range == (400, 700)
    assert not fam.is_variable
    vfam = variable_family()
    assert vfam.is_variable
    assert vfam.weight_range == (100, 900)
