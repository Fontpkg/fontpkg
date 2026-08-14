import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from fontpkg_generator.metadata_pb import as_list, parse

LICENSE_MAP = {
    "OFL": ("OFL-1.1", "OFL.txt"),
    "APACHE2": ("Apache-2.0", "LICENSE.txt"),
}


class UnsupportedLicense(Exception):
    pass


@dataclass(frozen=True)
class SourceInfo:
    repo: str
    path: str
    commit: str


def slugify(name: str) -> str:
    return re.sub(r"[\s_]+", "-", name.strip().lower())


def build_package(family_dir: Path, out_dir: Path, source: SourceInfo | None = None) -> Path:
    meta = parse((family_dir / "METADATA.pb").read_text(encoding="utf-8"))
    name = meta["name"]
    license_key = meta.get("license", "")
    if license_key not in LICENSE_MAP:
        raise UnsupportedLicense(
            f"{name}: license {license_key!r} is not redistributable by fontpkg "
            f"(supported: {sorted(LICENSE_MAP)})"
        )
    spdx, license_filename = LICENSE_MAP[license_key]
    license_path = family_dir / license_filename
    if not license_path.is_file():
        raise FileNotFoundError(f"{name}: expected license file {license_filename} not found")

    slug = slugify(name)
    module_name = f"fontpkg_{slug.replace('-', '_')}"
    axes = [a for a in as_list(meta.get("axes")) if isinstance(a, dict)]
    file_entries = _file_entries(as_list(meta["fonts"]), family_dir)
    if not file_entries:
        raise FileNotFoundError(f"{name}: no font binaries found in {family_dir}")
    version = _font_version(family_dir / Path(file_entries[0]["path"]).name)
    copyright_line = _copyright(as_list(meta["fonts"]))

    pkg_root = out_dir / f"fontpkg-{slug}"
    module_dir = pkg_root / "src" / module_name
    files_dir = module_dir / "files"
    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    files_dir.mkdir(parents=True)

    for entry in file_entries:
        filename = Path(entry["path"]).name
        shutil.copy2(family_dir / filename, files_dir / filename)
    shutil.copy2(license_path, pkg_root / "LICENSE")
    shutil.copy2(license_path, module_dir / "LICENSE")

    metadata = {
        "schema": 1,
        "family": name,
        "slug": slug,
        "version": version,
        "license": spdx,
        "copyright": copyright_line,
        "axes": [
            {"tag": a["tag"], "min": a["min_value"], "max": a["max_value"]} for a in axes
        ],
        "files": file_entries,
    }
    if source is not None:
        metadata["source"] = {"repo": source.repo, "path": source.path, "commit": source.commit}
    (module_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (module_dir / "__init__.py").write_text(_init_py(name), encoding="utf-8")
    (pkg_root / "pyproject.toml").write_text(
        _pyproject(name, slug, module_name, version, spdx), encoding="utf-8"
    )
    (pkg_root / "README.md").write_text(
        _readme(name, slug, spdx, copyright_line, source), encoding="utf-8"
    )
    return pkg_root


def _file_entries(fonts: list[dict[str, Any]], family_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for font in fonts:
        filename = font.get("filename", "")
        if not (family_dir / filename).is_file():
            continue
        variable = "[" in filename
        entries.append(
            {
                "path": f"files/{filename}",
                "style": font.get("style", "normal"),
                "weight": None if variable else int(font.get("weight", 400)),
                "variable": variable,
            }
        )
    return entries


def _font_version(font_path: Path) -> str:
    font = TTFont(str(font_path), lazy=True)
    revision = float(font["head"].fontRevision)
    font.close()
    if revision <= 0:
        raise ValueError(f"{font_path.name}: head.fontRevision is {revision}")
    return f"{revision:.3f}"


def _copyright(fonts: list[dict[str, Any]]) -> str:
    for font in fonts:
        if font.get("copyright"):
            return str(font["copyright"])
    return ""


def _init_py(name: str) -> str:
    return (
        "from pathlib import Path\n"
        "\n"
        f'FAMILY = "{name}"\n'
        "ROOT = Path(__file__).resolve().parent\n"
    )


def _pyproject(name: str, slug: str, module_name: str, version: str, spdx: str) -> str:
    return f"""\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "fontpkg-{slug}"
version = "{version}"
description = "{name} font family, packaged for Python by fontpkg"
readme = "README.md"
requires-python = ">=3.10"
license = "{spdx}"
license-files = ["LICENSE"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Topic :: Text Processing :: Fonts",
]

[project.entry-points."fontpkg.family"]
{slug.replace("-", "_")} = "{module_name}"

[tool.hatch.build.targets.wheel]
packages = ["src/{module_name}"]
"""


def _readme(
    name: str, slug: str, spdx: str, copyright_line: str, source: SourceInfo | None
) -> str:
    provenance = ""
    if source is not None:
        provenance = (
            f"\nUpstream: [{source.repo}]({source.repo}) at `{source.path}` "
            f"(commit `{source.commit[:12]}`).\n"
        )
    return f"""\
# fontpkg-{slug}

The **{name}** font family, packaged for Python by [fontpkg](https://pypi.org/project/fontpkg/).
Font binaries are redistributed unmodified under the `{spdx}` license (see `LICENSE`).

> {copyright_line}
{provenance}
```python
import fontpkg

path = fontpkg.path("{name}")
```
"""
