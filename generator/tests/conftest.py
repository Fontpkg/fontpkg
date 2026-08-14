from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

OFL_TEXT = (
    "Copyright 2020 The Testface Project Authors\n\n"
    "This Font Software is licensed under the SIL Open Font License, Version 1.1.\n"
)

METADATA_STATIC = """\
name: "Testface"
designer: "A. Designer"
license: "OFL"
category: "SANS_SERIF"
date_added: "2020-01-01"
fonts {
  name: "Testface"
  style: "normal"
  weight: 400
  filename: "Testface-Regular.ttf"
  post_script_name: "Testface-Regular"
  full_name: "Testface Regular"
  copyright: "Copyright 2020 The Testface Project Authors"
}
fonts {
  name: "Testface"
  style: "italic"
  weight: 400
  filename: "Testface-Italic.ttf"
  post_script_name: "Testface-Italic"
  full_name: "Testface Italic"
  copyright: "Copyright 2020 The Testface Project Authors"
}
subsets: "latin"
subsets: "latin-ext"
"""

METADATA_VARIABLE = """\
name: "Varface"
license: "OFL"
fonts {
  name: "Varface"
  style: "normal"
  weight: 400
  filename: "Varface[wght].ttf"
  copyright: "Copyright 2021 The Varface Project Authors"
}
axes {
  tag: "wght"
  min_value: 100.0
  max_value: 900.0
}
"""


def make_ttf(path: Path, revision: float = 1.5) -> Path:
    fb = FontBuilder(unitsPerEm=1000)
    glyph_order = [".notdef", "A"]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({ord("A"): "A"})
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 700))
    pen.lineTo((500, 700))
    pen.lineTo((500, 0))
    pen.closePath()
    glyph = pen.glyph()
    fb.setupGlyf({name: glyph for name in glyph_order})
    fb.setupHorizontalMetrics({name: (600, 0) for name in glyph_order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Testface", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    fb.font["head"].fontRevision = revision
    fb.save(str(path))
    return path


@pytest.fixture
def static_family_dir(tmp_path: Path) -> Path:
    family_dir = tmp_path / "testface"
    family_dir.mkdir()
    (family_dir / "METADATA.pb").write_text(METADATA_STATIC, encoding="utf-8")
    (family_dir / "OFL.txt").write_text(OFL_TEXT, encoding="utf-8")
    make_ttf(family_dir / "Testface-Regular.ttf", revision=2.137)
    make_ttf(family_dir / "Testface-Italic.ttf", revision=2.137)
    return family_dir


@pytest.fixture
def variable_family_dir(tmp_path: Path) -> Path:
    family_dir = tmp_path / "varface"
    family_dir.mkdir()
    (family_dir / "METADATA.pb").write_text(METADATA_VARIABLE, encoding="utf-8")
    (family_dir / "OFL.txt").write_text(OFL_TEXT, encoding="utf-8")
    make_ttf(family_dir / "Varface[wght].ttf", revision=1.002)
    return family_dir
