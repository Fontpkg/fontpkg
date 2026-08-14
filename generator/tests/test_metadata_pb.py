import pytest

from fontpkg_generator.metadata_pb import as_list, parse

SAMPLE = """\
name: "Testface"
designer: "A. Designer"
license: "OFL"
category: "SANS_SERIF"
fonts {
  name: "Testface"
  style: "normal"
  weight: 400
  filename: "Testface-Regular.ttf"
}
fonts {
  name: "Testface"
  style: "italic"
  weight: 400
  filename: "Testface-Italic.ttf"
}
axes {
  tag: "wght"
  min_value: 100.0
  max_value: 900.0
}
subsets: "latin"
subsets: "latin-ext"
"""


def test_parse_scalars_and_repeated_messages() -> None:
    meta = parse(SAMPLE)
    assert meta["name"] == "Testface"
    assert meta["license"] == "OFL"
    fonts = as_list(meta["fonts"])
    assert len(fonts) == 2
    assert fonts[0]["weight"] == 400
    assert fonts[1]["style"] == "italic"
    assert as_list(meta["subsets"]) == ["latin", "latin-ext"]


def test_parse_axes_floats() -> None:
    axes = as_list(parse(SAMPLE)["axes"])
    assert axes[0]["tag"] == "wght"
    assert axes[0]["min_value"] == 100.0
    assert axes[0]["max_value"] == 900.0


def test_as_list_wraps_single_message() -> None:
    meta = parse('name: "X"\nfonts {\n  weight: 700\n}\n')
    assert as_list(meta["fonts"]) == [{"weight": 700}]
    assert as_list(None) == []


def test_parse_escaped_quotes() -> None:
    meta = parse('copyright: "say \\"hi\\""')
    assert meta["copyright"] == 'say "hi"'


def test_parse_unbalanced_raises() -> None:
    with pytest.raises(ValueError):
        parse("fonts {\n  weight: 400\n")
