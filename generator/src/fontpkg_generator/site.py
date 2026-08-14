import importlib.resources
import json
import shutil
from pathlib import Path


def build_site(catalog_path: Path, packages_dir: Path, out_dir: Path) -> Path:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    fonts_dir = out_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    css_rules: list[str] = []
    entries: list[dict] = []
    for slug in sorted(catalog):
        entry = catalog[slug]
        module_dir = _module_dir(packages_dir, entry["package"])
        meta = json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
        for f in meta["files"]:
            src = module_dir / f["path"]
            dest_name = _dest_name(slug, f)
            shutil.copy2(src, fonts_dir / dest_name)
            css_rules.append(_font_face(entry, f, dest_name))
        entries.append(entry)
    template = (
        importlib.resources.files("fontpkg_generator") / "site_template.html"
    ).read_text(encoding="utf-8")
    html = template.replace("/*__FONT_FACES__*/", "\n".join(css_rules)).replace(
        "__FAMILY_DATA__", json.dumps(entries)
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    (out_dir / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return out_dir


def _module_dir(packages_dir: Path, package: str) -> Path:
    src_dir = packages_dir / package / "src"
    if not src_dir.is_dir():
        raise FileNotFoundError(f"built package not found: {packages_dir / package}")
    return next(src_dir.iterdir())


def _dest_name(slug: str, f: dict) -> str:
    style = f.get("style", "normal")
    if f.get("variable"):
        return f"{slug}-{style}.ttf"
    return f"{slug}-{f.get('weight', 400)}-{style}.ttf"


def _font_face(entry: dict, f: dict, dest_name: str) -> str:
    family = entry["family"]
    style = f.get("style", "normal")
    if f.get("variable") and entry.get("weight_range"):
        lo, hi = entry["weight_range"]
        weight = f"{lo} {hi}"
        fmt = "truetype-variations"
    else:
        weight = str(f.get("weight", 400))
        fmt = "truetype"
    return (
        f'@font-face {{ font-family: "{family}"; src: url("fonts/{dest_name}") '
        f'format("{fmt}"); font-weight: {weight}; font-style: {style}; font-display: swap; }}'
    )
