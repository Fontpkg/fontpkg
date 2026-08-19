import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from fontpkg_generator.build import SourceInfo, UnsupportedLicense, build_package, build_wheel
from fontpkg_generator.gh import REPO_URL, FamilyNotFound, fetch_family, google_dirname
from fontpkg_generator.site import build_site
from fontpkg_generator.sync import publish_pending, sync_families


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
    build.add_argument(
        "--post", type=int, default=None, help="append .postN to the package version"
    )
    sync = sub.add_parser("sync", help="rebuild families whose upstream changed")
    sync.add_argument("families", nargs="*", help="family slugs (default: --families-file)")
    sync.add_argument("--families-file", type=Path, default=None)
    sync.add_argument("--state", type=Path, default=Path("state.json"))
    sync.add_argument("--catalog", type=Path, default=Path("catalog.json"))
    sync.add_argument("--out", type=Path, default=Path("build"))
    sync.add_argument("--wheel", action="store_true", help="also build wheels with uv build")
    site = sub.add_parser("site", help="generate the static specimen site")
    site.add_argument("--catalog", type=Path, default=Path("catalog.json"))
    site.add_argument("--packages", type=Path, default=Path("build"))
    site.add_argument("--out", type=Path, default=Path("site-dist"))
    site.add_argument(
        "--state", type=Path, default=None, help="limit the site to published families"
    )
    pending = sub.add_parser("publish-pending", help="publish families not yet on PyPI")
    pending.add_argument("--state", type=Path, default=Path("state.json"))
    pending.add_argument("--out", type=Path, default=Path("build"))
    pending.add_argument(
        "--priority-file",
        type=Path,
        default=None,
        help="publish in this file's order (e.g. families.txt) instead of alphabetically",
    )
    args = parser.parse_args(argv)
    if args.command == "sync":
        return _sync(args)
    if args.command == "site":
        out = build_site(args.catalog, args.packages, args.out, state_path=args.state)
        print(f"site written to {out}")
        return 0
    if args.command == "publish-pending":
        return _publish_pending(args)
    return _build(args)


def _publish_pending(args: argparse.Namespace) -> int:
    priority = None
    if args.priority_file is not None:
        lines = args.priority_file.read_text(encoding="utf-8").splitlines()
        priority = [google_dirname(ln) for ln in lines if ln.strip() and not ln.startswith("#")]
    report = publish_pending(args.state, args.out, publisher=_uv_publish, priority=priority)
    for key in report.published:
        print(f"PUBLISHED {key}")
    for key in report.skipped:
        print(f"pending {key} (throttled or failed; will retry)")
    return 0


def _uv_publish(pkg_root: Path) -> bool:
    name = pkg_root.name
    result = subprocess.run(
        ["uv", "publish", "--check-url", f"https://pypi.org/simple/{name}/"]
        + [str(f) for f in sorted((pkg_root / "dist").glob("*"))],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _sync(args: argparse.Namespace) -> int:
    families = list(args.families)
    if args.families_file is not None:
        lines = args.families_file.read_text(encoding="utf-8").splitlines()
        families += [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if not families:
        print("error: no families given (pass slugs or --families-file)", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    wheel_builder = _build_wheel if args.wheel else None
    report = sync_families(
        families, args.state, args.out, wheel_builder=wheel_builder, catalog_path=args.catalog
    )
    for slug in report.unchanged:
        print(f"unchanged {slug}")
    for slug, version in report.built:
        print(f"built {slug} {version}")
    for slug, err in report.failed:
        print(f"FAIL {slug}: {err}", file=sys.stderr)
    if report.aborted_early:
        print(
            f"ABORTED after {len(report.failed)} consecutive network failures — "
            "stopping early rather than burning through the rest of the list; "
            "remaining families were left untouched for a later run.",
            file=sys.stderr,
        )
    return 1 if report.failed else 0


def _build(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in args.families:
        try:
            pkg_root = _build_one(name, args.out, args.from_dir, args.post)
        except (FamilyNotFound, UnsupportedLicense, FileNotFoundError) as err:
            print(f"SKIP {name}: {err}", file=sys.stderr)
            failures += 1
            continue
        print(f"built {pkg_root}")
        if args.wheel:
            _build_wheel(pkg_root)
    return 1 if failures else 0


def _build_one(name: str, out: Path, from_dir: Path | None, post: int | None = None) -> Path:
    if from_dir is not None:
        return build_package(from_dir, out, source=None, post=post)
    with tempfile.TemporaryDirectory(prefix="fontpkg-fetch-") as tmp:
        fetched = fetch_family(name, Path(tmp))
        source = SourceInfo(repo=REPO_URL, path=fetched.repo_path, commit=fetched.commit)
        return build_package(fetched.family_dir, out, source=source, post=post)


def _build_wheel(pkg_root: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(pkg_root / "dist"), str(pkg_root)],
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
