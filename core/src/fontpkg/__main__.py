import argparse
import sys
import urllib.error

from fontpkg import FontpkgError, families
from fontpkg import path as font_path
from fontpkg._catalog import fetch_catalog, search_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fontpkg")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="list installed font families")
    path_cmd = sub.add_parser("path", help="print the file path for a family")
    path_cmd.add_argument("family")
    path_cmd.add_argument("--weight", default="400")
    path_cmd.add_argument("--style", default="normal")
    path_cmd.add_argument("--nearest", action="store_true")
    search_cmd = sub.add_parser("search", help="search installable font families (network)")
    search_cmd.add_argument("query", nargs="?", help="match against family, slug, or category")
    search_cmd.add_argument(
        "--category", default=None, help="restrict to a category (sans, serif, mono, ...)"
    )
    search_cmd.add_argument(
        "--catalog-url", default=None, help="catalog URL or file path (default: fontpkg repo)"
    )
    args = parser.parse_args(argv)

    if args.command in (None, "list"):
        return _list()
    if args.command == "search":
        return _search(args)
    return _path(args)


def _list() -> int:
    fams = families()
    if not fams:
        print("no font families installed (try: uv add fontpkg-roboto)")
        return 0
    width = max(len(s) for s in fams)
    for slug in sorted(fams):
        fam = fams[slug]
        weights = "variable" if fam.is_variable else ",".join(map(str, fam.weights))
        print(
            f"{slug:{width}}  v{fam.version}  {fam.license}  "
            f"styles={'/'.join(fam.styles)}  weights={weights}  range={fam.weight_range}"
        )
    return 0


def _search(args: argparse.Namespace) -> int:
    try:
        catalog = fetch_catalog(args.catalog_url)
    except (urllib.error.URLError, OSError) as err:
        print(f"error: could not fetch catalog: {err}", file=sys.stderr)
        return 1
    matches = search_catalog(catalog, args.query, category=args.category)
    if not matches:
        print(f"no installable families match {args.query!r}")
        return 0
    installed = set(families())
    width = max(len(e["slug"]) for e in matches)
    for e in matches:
        if e["variable"] and e["weight_range"]:
            weights = f"wght {e['weight_range'][0]}-{e['weight_range'][1]}"
        else:
            weights = ",".join(map(str, e["weights"]))
        mark = "  [installed]" if e["slug"] in installed else ""
        print(
            f"{e['slug']:{width}}  {e['license']:10} styles={'/'.join(e['styles'])} "
            f"{weights}  uv add {e['package']}{mark}"
        )
    return 0


def _path(args: argparse.Namespace) -> int:
    weight: int | str = int(args.weight) if args.weight.isdigit() else args.weight
    try:
        print(font_path(args.family, weight=weight, style=args.style, nearest=args.nearest))
    except FontpkgError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
