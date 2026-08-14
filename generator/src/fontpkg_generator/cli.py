import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from fontpkg_generator.build import SourceInfo, UnsupportedLicense, build_package
from fontpkg_generator.gh import REPO_URL, FamilyNotFound, fetch_family


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fontpkg-gen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build fontpkg-<family> packages")
    build.add_argument("families", nargs="+", help="family names or slugs (e.g. roboto)")
    build.add_argument("--out", type=Path, default=Path("build"))
    build.add_argument(
        "--from-dir",
        type=Path,
        default=None,
        help="build from a local google/fonts family directory instead of fetching",
    )
    build.add_argument("--wheel", action="store_true", help="also build wheels with uv build")
    args = parser.parse_args(argv)
    return _build(args)


def _build(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in args.families:
        try:
            pkg_root = _build_one(name, args.out, args.from_dir)
        except (FamilyNotFound, UnsupportedLicense, FileNotFoundError) as err:
            print(f"SKIP {name}: {err}", file=sys.stderr)
            failures += 1
            continue
        print(f"built {pkg_root}")
        if args.wheel:
            _build_wheel(pkg_root)
    return 1 if failures else 0


def _build_one(name: str, out: Path, from_dir: Path | None) -> Path:
    if from_dir is not None:
        return build_package(from_dir, out, source=None)
    with tempfile.TemporaryDirectory(prefix="fontpkg-fetch-") as tmp:
        fetched = fetch_family(name, Path(tmp))
        source = SourceInfo(repo=REPO_URL, path=fetched.repo_path, commit=fetched.commit)
        return build_package(fetched.family_dir, out, source=source)


def _build_wheel(pkg_root: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(pkg_root / "dist"), str(pkg_root)],
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
