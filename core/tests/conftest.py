from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def make_ttf(path: Path, family: str = "Testface", revision: float = 1.5) -> Path:
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
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    fb.font["head"].fontRevision = revision
    fb.save(str(path))
    return path


@pytest.fixture
def ttf_factory(tmp_path: Path):
    def _make(name: str = "Testface-Regular.ttf", revision: float = 1.5) -> Path:
        return make_ttf(tmp_path / name, revision=revision)

    return _make
