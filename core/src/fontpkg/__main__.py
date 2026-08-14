import argparse
import sys

from fontpkg import FontpkgError, families
from fontpkg import path as font_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fontpkg")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="list installed font families")
    path_cmd = sub.add_parser("path", help="print the file path for a family")
    path_cmd.add_argument("family")
    path_cmd.add_argument("--weight", default="400")
    path_cmd.add_argument("--style", default="normal")
    path_cmd.add_argument("--nearest", action="store_true")
    args = parser.parse_args(argv)

    if args.command in (None, "list"):
        return _list()
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
