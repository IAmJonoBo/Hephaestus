"""Tests for wheelhouse release helpers."""

from __future__ import annotations

import contextlib
import io
import tarfile
from pathlib import Path
from typing import Any

import pytest

from hephaestus import release


def _make_wheelhouse_tarball(tmp_path: Path) -> Path:
    wheelhouse_dir = tmp_path / "wheelhouse-src"
    wheelhouse_dir.mkdir()
    wheelhouse_dir.joinpath("sample-0.0.1-py3-none-any.whl").write_bytes(b"placeholder wheel")
    tar_path = tmp_path / "wheelhouse.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(wheelhouse_dir, arcname=".")
    return tar_path


def test_download_wheelhouse_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    def fake_fetch_release(repository: str, tag: str | None, token: str | None) -> dict[str, Any]:
        return {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                }
            ]
        }

    def fake_download_asset(
        asset: release.ReleaseAsset, destination: Path, token: str | None, overwrite: bool
    ) -> Path:
        destination.write_bytes(tar_path.read_bytes())
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        tag="v1.2.3",
    )

    assert result.asset.name == "hephaestus-1.2.3-wheelhouse.tar.gz"
    assert result.archive_path.exists()
    assert result.extracted_path is not None
    extracted_files = list(result.extracted_path.glob("*.whl"))
    assert extracted_files and extracted_files[0].name.endswith("sample-0.0.1-py3-none-any.whl")


def test_extract_archive_blocks_path_escape(tmp_path: Path) -> None:
    archive_path = tmp_path / "escape.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo(name="../evil.txt")
        data = b"oops"
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))

    with pytest.raises(release.ReleaseError, match="Refusing to extract"):
        release.extract_archive(archive_path, destination=tmp_path / "extract")


def test_install_from_directory_invokes_pip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel_dir = tmp_path / "wheel-dir"
    wheel_dir.mkdir()
    wheel_file = wheel_dir / "pkg.whl"
    wheel_file.write_bytes(b"wheel")

    called = []

    def fake_check_call(cmd: list[str], **_: Any) -> None:
        called.append(cmd)

    monkeypatch.setattr(release.subprocess, "check_call", fake_check_call)

    release.install_from_directory(
        wheel_dir, python_executable="python", pip_args=["--quiet"], upgrade=False
    )

    assert called
    command = called[0]
    assert command[:3] == ["python", "-m", "pip"]
    assert "--quiet" in command
    assert "pkg.whl" in command[-1]
    assert "--upgrade" not in command


def test_install_from_archive_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)
    extracted_dirs: list[Path] = []

    def fake_install_from_directory(directory: Path, **_: Any) -> None:
        extracted_dirs.append(directory)

    monkeypatch.setattr(release, "install_from_directory", fake_install_from_directory)

    extracted = release.install_from_archive(tar_path, cleanup=True)

    assert extracted_dirs == [extracted]
    assert not extracted.exists()


def test_default_download_dir_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = (tmp_path / "override-cache").resolve()
    monkeypatch.setenv("HEPHAESTUS_RELEASE_CACHE", str(target))
    result = release.default_download_dir()
    assert result == target


def test_default_download_dir_platform_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("HEPHAESTUS_RELEASE_CACHE", raising=False)

    monkeypatch.setattr(release.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalData"))
    windows_dir = release.default_download_dir()
    assert windows_dir == (tmp_path / "LocalData" / "hephaestus" / "wheelhouses").resolve()

    monkeypatch.setattr(release.sys, "platform", "darwin")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    darwin_dir = release.default_download_dir()
    assert darwin_dir.name == "wheelhouses"
    assert darwin_dir.parent.name == "hephaestus"

    monkeypatch.setattr(release.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    linux_dir = release.default_download_dir()
    assert linux_dir == (tmp_path / "xdg" / "hephaestus" / "wheelhouses").resolve()


def test_build_request_sets_headers() -> None:
    request = release._build_request(
        "https://example.invalid/resource", token="abc123", accept="data"
    )
    assert request.get_header("Accept") == "data"
    assert request.get_header("User-agent") == "hephaestus-wheelhouse-client"
    assert request.get_header("Authorization") == "Bearer abc123"


def test_fetch_release_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b'{"assets": []}'
    captured = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: Any) -> bool:  # pragma: no cover - normal flow
            return False

        def read(self) -> bytes:
            return payload

    def fake_urlopen(request: Any) -> FakeResponse:
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(release.urllib.request, "urlopen", fake_urlopen)

    data = release._fetch_release("owner/repo", tag=None, token="token")

    assert data == {"assets": []}
    assert captured["url"].endswith("/releases/latest")


def test_fetch_release_validates_repository() -> None:
    with pytest.raises(release.ReleaseError, match="owner/repository"):
        release._fetch_release("invalid", tag=None, token=None)


def test_pick_asset_requires_match() -> None:
    with pytest.raises(release.ReleaseError, match="Could not find asset"):
        release._pick_asset({"assets": [{"name": "other.txt"}]}, "*wheelhouse*.tar.gz")


def test_download_asset_respects_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    asset = release.ReleaseAsset(
        name="archive.tar.gz",
        download_url="https://example.invalid/archive.tar.gz",
        size=3,
    )
    destination = tmp_path / asset.name
    destination.write_bytes(b"old")

    with pytest.raises(release.ReleaseError, match="already exists"):
        release._download_asset(asset, destination, token=None, overwrite=False)

    payload = b"new"

    def fake_urlopen(request: Any) -> contextlib.AbstractContextManager[io.BytesIO]:
        assert request.get_header("Authorization") == "Bearer token"
        return contextlib.closing(io.BytesIO(payload))

    monkeypatch.setattr(release.urllib.request, "urlopen", fake_urlopen)

    result_path = release._download_asset(asset, destination, token="token", overwrite=True)
    assert result_path.read_bytes() == payload


def test_download_wheelhouse_without_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    monkeypatch.setattr(
        release,
        "_fetch_release",
        lambda repository, tag, token: {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                }
            ]
        },
    )

    def fake_download(
        asset: release.ReleaseAsset, destination: Path, *_args: Any, **_kwargs: Any
    ) -> Path:
        destination.write_bytes(tar_path.read_bytes())
        return destination

    monkeypatch.setattr(release, "_download_asset", fake_download)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        extract=False,
    )

    assert result.extracted_path is None
    assert result.archive_path.exists()


def test_sanitize_asset_name_strips_path_separators() -> None:
    """Test that asset names are sanitized to prevent path traversal."""
    # Normal names should pass through
    assert release._sanitize_asset_name("wheelhouse.tar.gz") == "wheelhouse.tar.gz"
    assert release._sanitize_asset_name("hephaestus-0.1.0.tar.gz") == "hephaestus-0.1.0.tar.gz"

    # Path separators should be stripped
    assert release._sanitize_asset_name("../../etc/passwd") == "passwd"
    assert release._sanitize_asset_name("/absolute/path/file.tar.gz") == "file.tar.gz"
    assert release._sanitize_asset_name("dir/subdir/file.tar.gz") == "file.tar.gz"

    # Windows-style paths
    assert release._sanitize_asset_name("C:\\Windows\\file.tar.gz") == "file.tar.gz"
    assert release._sanitize_asset_name("..\\..\\file.tar.gz") == "file.tar.gz"

    # Double dots should be replaced
    assert release._sanitize_asset_name("file..tar.gz") == "file_.tar.gz"

    # Empty or dangerous names should raise
    with pytest.raises(release.ReleaseError, match="empty or unsafe"):
        release._sanitize_asset_name(".")

    with pytest.raises(release.ReleaseError, match="empty or unsafe"):
        release._sanitize_asset_name("..")

    with pytest.raises(release.ReleaseError, match="empty or unsafe"):
        release._sanitize_asset_name("/")


def test_fetch_release_validates_timeout() -> None:
    """Test that _fetch_release validates timeout parameter."""
    with pytest.raises(release.ReleaseError, match="Timeout must be positive"):
        release._fetch_release("owner/repo", None, None, timeout=0)
    
    with pytest.raises(release.ReleaseError, match="Timeout must be positive"):
        release._fetch_release("owner/repo", None, None, timeout=-1)


def test_fetch_release_validates_max_retries() -> None:
    """Test that _fetch_release validates max_retries parameter."""
    with pytest.raises(release.ReleaseError, match="Max retries must be at least 1"):
        release._fetch_release("owner/repo", None, None, max_retries=0)
    
    with pytest.raises(release.ReleaseError, match="Max retries must be at least 1"):
        release._fetch_release("owner/repo", None, None, max_retries=-1)


def test_download_asset_validates_timeout(tmp_path: Path) -> None:
    """Test that _download_asset validates timeout parameter."""
    asset = release.ReleaseAsset(
        name="test.tar.gz",
        download_url="https://example.invalid/test.tar.gz",
        size=100,
    )
    destination = tmp_path / "test.tar.gz"
    
    with pytest.raises(release.ReleaseError, match="Timeout must be positive"):
        release._download_asset(asset, destination, None, False, timeout=0)
    
    with pytest.raises(release.ReleaseError, match="Timeout must be positive"):
        release._download_asset(asset, destination, None, False, timeout=-1)


def test_download_asset_validates_max_retries(tmp_path: Path) -> None:
    """Test that _download_asset validates max_retries parameter."""
    asset = release.ReleaseAsset(
        name="test.tar.gz",
        download_url="https://example.invalid/test.tar.gz",
        size=100,
    )
    destination = tmp_path / "test.tar.gz"
    
    with pytest.raises(release.ReleaseError, match="Max retries must be at least 1"):
        release._download_asset(asset, destination, None, False, max_retries=0)
    
    with pytest.raises(release.ReleaseError, match="Max retries must be at least 1"):
        release._download_asset(asset, destination, None, False, max_retries=-1)

