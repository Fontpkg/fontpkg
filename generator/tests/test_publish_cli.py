import json
import subprocess
import urllib.error
from pathlib import Path

import fontpkg_generator.cli as cli


def make_pkg(tmp_path: Path, slug: str = "testface", version: str = "1.010") -> Path:
    pkg_root = tmp_path / f"fontpkg-{slug}"
    module_dir = pkg_root / "src" / f"fontpkg_{slug}"
    module_dir.mkdir(parents=True)
    (module_dir / "metadata.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    (pkg_root / "dist").mkdir()
    (pkg_root / "dist" / f"fontpkg_{slug}-{version}-py3-none-any.whl").write_bytes(b"")
    return pkg_root


def test_read_version_from_metadata_json(tmp_path: Path) -> None:
    pkg_root = make_pkg(tmp_path, version="2.137")
    assert cli._read_version(pkg_root) == "2.137"


def test_read_version_missing_src_returns_none(tmp_path: Path) -> None:
    assert cli._read_version(tmp_path / "nope") is None


def test_pypi_has_version_true_on_200(monkeypatch) -> None:
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda url, timeout=15: FakeResponse())
    assert cli._pypi_has_version("fontpkg-inter", "4.1") is True


def test_pypi_has_version_false_on_404(monkeypatch) -> None:
    def raise_404(url, timeout=15):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(cli.urllib.request, "urlopen", raise_404)
    assert cli._pypi_has_version("fontpkg-nope", "1.0") is False


def test_uv_publish_skips_upload_when_version_already_on_pypi(tmp_path, monkeypatch) -> None:
    pkg_root = make_pkg(tmp_path)
    monkeypatch.setattr(cli, "_pypi_has_version", lambda name, version: True)

    def boom(*a, **k):
        raise AssertionError("uv publish should not be invoked when already on PyPI")

    monkeypatch.setattr(cli.subprocess, "run", boom)
    assert cli._uv_publish(pkg_root) is True


def test_uv_publish_attempts_upload_when_not_on_pypi(tmp_path, monkeypatch) -> None:
    pkg_root = make_pkg(tmp_path)
    monkeypatch.setattr(cli, "_pypi_has_version", lambda name, version: False)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._uv_publish(pkg_root) is True
    assert calls and calls[0][:2] == ["uv", "publish"]


def test_uv_publish_reports_failure_reason(tmp_path, monkeypatch, capsys) -> None:
    pkg_root = make_pkg(tmp_path)
    monkeypatch.setattr(cli, "_pypi_has_version", lambda name, version: False)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=2, stdout="", stderr="400 File already exists"
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._uv_publish(pkg_root) is False
    assert "File already exists" in capsys.readouterr().err
