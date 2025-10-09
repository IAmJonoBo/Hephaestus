"""Tests for wheelhouse release helpers."""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import hashlib
import io
import json
import shutil
import tarfile
import urllib.error
from datetime import timedelta
from email.message import Message
from pathlib import Path
from typing import Any, Literal

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from hephaestus import release, resource_forks


def _make_wheelhouse_tarball(tmp_path: Path) -> Path:
    wheelhouse_dir = tmp_path / "wheelhouse-src"
    wheelhouse_dir.mkdir()
    wheelhouse_dir.joinpath("sample-0.0.1-py3-none-any.whl").write_bytes(b"placeholder wheel")
    tar_path = tmp_path / "wheelhouse.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(wheelhouse_dir, arcname=".")
    return tar_path


def _make_wheelhouse_tarball_with_cruft(tmp_path: Path) -> Path:
    wheelhouse_dir = tmp_path / "wheelhouse-cruft"
    wheelhouse_dir.mkdir()
    wheelhouse_dir.joinpath("sample-0.0.1-py3-none-any.whl").write_bytes(b"placeholder wheel")
    (wheelhouse_dir / ".DS_Store").write_text("metadata", encoding="utf-8")
    (wheelhouse_dir / "._hidden").write_text("metadata", encoding="utf-8")
    (wheelhouse_dir / "IconX").write_text("icon", encoding="utf-8")
    macos_dir = wheelhouse_dir / "__MACOSX"
    macos_dir.mkdir()
    (macos_dir / "extra").write_text("metadata", encoding="utf-8")

    tar_path = tmp_path / "wheelhouse-cruft.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(wheelhouse_dir, arcname=".")
    return tar_path


def _create_sigstore_bundle(
    tmp_path: Path,
    artifact: Path,
    *,
    identity_uri: str = "https://example.invalid/repos/IAmJonoBo/Hephaestus/actions/workflows/release.yml@refs/tags/v1.2.3",
) -> Path:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "github-actions")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(tz=dt.UTC) - timedelta(minutes=1))
        .not_valid_after(dt.datetime.now(tz=dt.UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.UniformResourceIdentifier(identity_uri),
                    x509.RFC822Name("github-actions@github.com"),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    digest = hashlib.sha256(artifact.read_bytes()).digest()

    bundle = {
        "mediaType": "application/vnd.dev.sigstore.bundle+json;version=0.3",
        "messageSignature": {
            "messageDigest": {
                "algorithm": "SHA2_256",
                "digest": base64.b64encode(digest).decode("ascii"),
            },
            "signature": base64.b64encode(b"signature").decode("ascii"),
        },
        "verificationMaterial": {
            "x509CertificateChain": {
                "certificates": [
                    {
                        "rawBytes": base64.b64encode(
                            certificate.public_bytes(serialization.Encoding.DER)
                        ).decode("ascii"),
                    }
                ]
            },
            "tlogEntries": [],
        },
    }

    bundle_path = tmp_path / "wheelhouse.sigstore"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle_path


def test_download_wheelhouse_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
        return {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        }

    def fake_download_asset(
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        else:
            destination.write_text(
                f"{digest}  hephaestus-1.2.3-wheelhouse.tar.gz\n", encoding="utf-8"
            )
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


def test_verify_sigstore_bundle_valid(tmp_path: Path) -> None:
    artifact = tmp_path / "archive.tar.gz"
    artifact.write_bytes(b"artifact")
    identity = "https://example.invalid/repos/IAmJonoBo/Hephaestus/actions/workflows/release.yml@refs/tags/v1.2.3"
    bundle_path = _create_sigstore_bundle(tmp_path, artifact, identity_uri=identity)

    result = release._verify_sigstore_bundle(
        bundle_path,
        artifact,
        identity_patterns=[identity, "github-actions@github.com"],
    )

    assert identity in result.identities
    assert "github-actions@github.com" in result.identities


def test_verify_sigstore_bundle_accepts_multiple_patterns(tmp_path: Path) -> None:
    artifact = tmp_path / "archive.tar.gz"
    artifact.write_bytes(b"artifact")
    identity = "https://example.invalid/repos/IAmJonoBo/Hephaestus/actions/workflows/release.yml@refs/tags/v1.2.3"
    bundle_path = _create_sigstore_bundle(tmp_path, artifact, identity_uri=identity)

    wildcard = "https://example.invalid/repos/*/Hephaestus/actions/workflows/*"
    result = release._verify_sigstore_bundle(
        bundle_path,
        artifact,
        identity_patterns=["https://example.invalid/repos/Other/*", wildcard],
    )

    assert identity in result.identities
    assert wildcard not in result.identities


def test_verify_sigstore_bundle_identity_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "archive.tar.gz"
    artifact.write_bytes(b"artifact")
    bundle_path = _create_sigstore_bundle(tmp_path, artifact)

    with pytest.raises(release.ReleaseError, match="Sigstore identity mismatch"):
        release._verify_sigstore_bundle(
            bundle_path,
            artifact,
            identity_patterns=["https://example.invalid/other"],
        )


def test_verify_sigstore_bundle_digest_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "archive.tar.gz"
    artifact.write_bytes(b"artifact")
    bundle_path = _create_sigstore_bundle(tmp_path, artifact)
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["messageSignature"]["messageDigest"]["digest"] = base64.b64encode(b"bad-digest").decode(
        "ascii"
    )
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(release.ReleaseError, match="Sigstore bundle digest did not match"):
        release._verify_sigstore_bundle(bundle_path, artifact)


def test_extract_archive_blocks_path_escape(tmp_path: Path) -> None:
    archive_path = tmp_path / "escape.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo(name="../evil.txt")
        data = b"oops"
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))

    with pytest.raises(release.ReleaseError, match="Refusing to extract"):
        release.extract_archive(archive_path, destination=tmp_path / "extract")


def test_extract_archive_sanitizes_resource_forks(tmp_path: Path) -> None:
    archive_path = _make_wheelhouse_tarball_with_cruft(tmp_path)

    destination = release.extract_archive(archive_path, destination=tmp_path / "extracted")

    wheel_files = list(destination.glob("*.whl"))
    assert wheel_files, "Expected wheel file to remain after sanitisation"
    assert not list(destination.glob(".DS_Store"))
    assert not list(destination.glob("__MACOSX"))
    assert not list(destination.glob("._hidden"))
    assert not list(destination.glob("IconX"))
    assert not resource_forks.verify_clean(destination)


def test_extract_archive_overwrite_existing_destination(tmp_path: Path) -> None:
    archive_path = _make_wheelhouse_tarball(tmp_path)
    destination = tmp_path / "dest"
    destination.mkdir()
    marker = destination / "old.txt"
    marker.write_text("stale", encoding="utf-8")

    extracted = release.extract_archive(archive_path, destination=destination, overwrite=True)

    assert extracted == destination
    assert not marker.exists()
    assert list(extracted.glob("*.whl"))


def test_extract_archive_raises_on_sanitize_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = _make_wheelhouse_tarball(tmp_path)

    failing_report = resource_forks.SanitizationReport(
        errors=[(Path(".__MACOSX"), "permission denied")]
    )
    monkeypatch.setattr(release.resource_forks, "sanitize_path", lambda _path: failing_report)

    with pytest.raises(release.ReleaseError, match="Failed to remove resource fork artefact"):
        release.extract_archive(archive_path, destination=tmp_path / "extract")


def test_extract_archive_raises_when_residuals_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = _make_wheelhouse_tarball(tmp_path)

    clean_report = resource_forks.SanitizationReport()
    monkeypatch.setattr(release.resource_forks, "sanitize_path", lambda _path: clean_report)
    monkeypatch.setattr(
        release.resource_forks,
        "verify_clean",
        lambda _path: [Path("wheelhouse/__MACOSX")],
    )

    with pytest.raises(release.ReleaseError, match="Resource fork artefacts remain"):
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


def test_install_from_directory_raises_on_sanitize_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel_dir = tmp_path / "wheel-dir"
    wheel_dir.mkdir()
    wheel_dir.joinpath("pkg.whl").write_bytes(b"wheel")

    failing_report = resource_forks.SanitizationReport(
        errors=[(wheel_dir / "._bad", "permission denied")]
    )
    monkeypatch.setattr(release.resource_forks, "sanitize_path", lambda _path: failing_report)
    called = False

    def _never_called(_cmd: list[str], **_kwargs: Any) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(release.subprocess, "check_call", _never_called)

    with pytest.raises(release.ReleaseError, match="Failed to remove resource fork artefact"):
        release.install_from_directory(wheel_dir)

    assert called is False


def test_install_from_directory_raises_on_residuals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel_dir = tmp_path / "wheel-dir"
    wheel_dir.mkdir()
    wheel_dir.joinpath("pkg.whl").write_bytes(b"wheel")

    clean_report = resource_forks.SanitizationReport()
    monkeypatch.setattr(release.resource_forks, "sanitize_path", lambda _path: clean_report)
    monkeypatch.setattr(release.resource_forks, "verify_clean", lambda _path: [wheel_dir / "._bad"])
    called = False

    def _never_called(_cmd: list[str], **_kwargs: Any) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(release.subprocess, "check_call", _never_called)

    with pytest.raises(release.ReleaseError, match="Resource fork artefacts remain"):
        release.install_from_directory(wheel_dir)

    assert called is False


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

        def __exit__(self, *_args: Any) -> Literal[False]:  # pragma: no cover - normal flow
            return False

        def read(self) -> bytes:
            return payload

    def fake_urlopen(request: Any, *, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(release.urllib.request, "urlopen", fake_urlopen)

    data = release._fetch_release("owner/repo", tag=None, token="token")

    assert data == {"assets": []}
    assert captured["url"].endswith("/releases/latest")
    assert captured["timeout"] == release.DEFAULT_TIMEOUT


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

    def fake_urlopen(
        request: Any, *, timeout: float
    ) -> contextlib.AbstractContextManager[io.BytesIO]:
        assert request.get_header("Authorization") == "Bearer token"
        assert timeout == release.DEFAULT_TIMEOUT
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
        lambda repository, tag, token, *, timeout, max_retries: {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        },
    )

    def fake_download(
        asset: release.ReleaseAsset,
        destination: Path,
        *_args: Any,
        timeout: float,
        max_retries: int,
        **_kwargs: Any,
    ) -> Path:
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        else:
            digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
            destination.write_text(
                f"{digest}  hephaestus-1.2.3-wheelhouse.tar.gz\n", encoding="utf-8"
            )
        return destination

    monkeypatch.setattr(release, "_download_asset", fake_download)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        extract=False,
    )

    assert result.extracted_path is None
    assert result.archive_path.exists()


def test_download_wheelhouse_with_sigstore_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    identity = "https://example.invalid/repos/IAmJonoBo/Hephaestus/actions/workflows/release.yml@refs/tags/v1.2.3"

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
        return {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sigstore",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sigstore",
                    "size": 300,
                },
            ]
        }

    def fake_download_asset(
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        elif asset.name.endswith(".sha256"):
            destination.write_text(
                f"{digest}  hephaestus-1.2.3-wheelhouse.tar.gz\n",
                encoding="utf-8",
            )
        else:
            archive_path = destination.parent / "hephaestus-1.2.3-wheelhouse.tar.gz"
            bundle_path = _create_sigstore_bundle(
                destination.parent, archive_path, identity_uri=identity
            )
            shutil.move(bundle_path, destination)
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        tag="v1.2.3",
        sigstore_bundle_pattern="*.sigstore",
        sigstore_identities=[identity],
        require_sigstore=True,
    )

    assert result.sigstore_path is not None
    assert result.manifest_path is not None
    assert result.archive_path.exists()


def test_download_wheelhouse_requires_sigstore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()

    monkeypatch.setattr(
        release,
        "_fetch_release",
        lambda repository, tag, token, *, timeout, max_retries: {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        },
    )

    def fake_download(
        asset: release.ReleaseAsset,
        destination: Path,
        *_args: Any,
        timeout: float,
        max_retries: int,
        **_kwargs: Any,
    ) -> Path:
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        else:
            destination.write_text(
                f"{digest}  hephaestus-1.2.3-wheelhouse.tar.gz\n", encoding="utf-8"
            )
        return destination

    monkeypatch.setattr(release, "_download_asset", fake_download)

    with pytest.raises(release.ReleaseError, match="Sigstore attestation required"):
        release.download_wheelhouse(
            repository="IAmJonoBo/Hephaestus",
            destination_dir=tmp_path / "downloads",
            sigstore_bundle_pattern="*.sigstore",
            require_sigstore=True,
        )


def test_download_wheelhouse_require_sigstore_without_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()

    monkeypatch.setattr(
        release,
        "_fetch_release",
        lambda repository, tag, token, *, timeout, max_retries: {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        },
    )

    monkeypatch.setattr(
        release,
        "_download_asset",
        lambda asset, destination, *_args, **_kwargs: (
            destination.write_bytes(tar_path.read_bytes())
            if asset.name.endswith(".tar.gz")
            else destination.write_text(
                f"{digest}  hephaestus-1.2.3-wheelhouse.tar.gz\n", encoding="utf-8"
            )
        ),
    )

    with pytest.raises(
        release.ReleaseError,
        match="Sigstore attestation required but no bundle pattern",
    ):
        release.download_wheelhouse(
            repository="IAmJonoBo/Hephaestus",
            destination_dir=tmp_path / "downloads",
            sigstore_bundle_pattern=None,
            require_sigstore=True,
        )


def test_download_wheelhouse_rejects_allow_unsigned_with_require_sigstore() -> None:
    with pytest.raises(
        release.ReleaseError,
        match="Sigstore attestation cannot be required when allow_unsigned is enabled",
    ):
        release.download_wheelhouse(
            repository="IAmJonoBo/Hephaestus",
            destination_dir=Path.cwd(),
            allow_unsigned=True,
            require_sigstore=True,
        )


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
    assert release._sanitize_asset_name("file..tar.gz") == "file_tar.gz"

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


def test_open_with_retries_handles_transient_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """_open_with_retries retries on 5xx errors and eventually succeeds."""

    attempts: list[float] = []

    class FakeResponse(io.BytesIO):
        def __enter__(self) -> FakeResponse:  # pragma: no cover - trivial
            return self

        def __exit__(self, *_args: Any) -> None:  # pragma: no cover - normal flow
            return None

    def fake_urlopen(request: Any, *, timeout: float) -> FakeResponse:
        attempts.append(timeout)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                502,
                "bad gateway",
                Message(),
                io.BytesIO(b"error"),
            )
        return FakeResponse(b"ok")

    sleeps: list[float] = []
    monkeypatch.setattr(release.time, "sleep", sleeps.append)
    monkeypatch.setattr(release.urllib.request, "urlopen", fake_urlopen)

    request = release._build_request("https://example.invalid/resource", token=None)
    response = release._open_with_retries(
        request,
        timeout=1.25,
        max_retries=3,
        description="test",
    )

    with contextlib.closing(response) as fh:
        assert fh.read() == b"ok"

    assert attempts == [1.25, 1.25]
    assert sleeps == [release._BACKOFF_INITIAL]


def test_open_with_retries_raises_after_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """_open_with_retries propagates the final URLError after exhausting retries."""

    def fake_urlopen(_request: Any, *, timeout: float) -> Any:
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(release.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(release.time, "sleep", lambda _delay: None)

    request = release._build_request("https://example.invalid/resource", token=None)

    with pytest.raises(urllib.error.URLError):
        release._open_with_retries(
            request,
            timeout=0.75,
            max_retries=2,
            description="test",
        )


def test_download_wheelhouse_propagates_timeout_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """download_wheelhouse forwards timeout/retry configuration to helpers."""

    fetch_args: dict[str, Any] = {}
    download_args: dict[str, Any] = {}
    tar_path = _make_wheelhouse_tarball(tmp_path)

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
        fetch_args.update(
            {
                "repository": repository,
                "tag": tag,
                "token": token,
                "timeout": timeout,
                "max_retries": max_retries,
            }
        )
        return {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        }

    def fake_download_asset(
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        download_args.update(
            {
                "asset": asset,
                "destination": destination,
                "token": token,
                "overwrite": overwrite,
                "timeout": timeout,
                "max_retries": max_retries,
            }
        )
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        else:
            destination.write_text(
                f"{hashlib.sha256(tar_path.read_bytes()).hexdigest()}  hephaestus-1.2.3-wheelhouse.tar.gz\n",
                encoding="utf-8",
            )
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        timeout=3.5,
        max_retries=4,
    )

    assert result.archive_path.exists()
    assert fetch_args == {
        "repository": "IAmJonoBo/Hephaestus",
        "tag": None,
        "token": None,
        "timeout": 3.5,
        "max_retries": 4,
    }
    assert download_args["timeout"] == 3.5
    assert download_args["max_retries"] == 4


def test_download_wheelhouse_raises_when_manifest_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
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
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        destination.write_bytes(tar_path.read_bytes())
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    with pytest.raises(release.ReleaseError, match="checksum manifest"):
        release.download_wheelhouse(
            repository="IAmJonoBo/Hephaestus",
            destination_dir=tmp_path / "downloads",
        )


def test_download_wheelhouse_raises_on_checksum_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
        return {
            "assets": [
                {
                    "name": "hephaestus-1.2.3-wheelhouse.tar.gz",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.tar.gz",
                    "size": tar_path.stat().st_size,
                },
                {
                    "name": "hephaestus-1.2.3-wheelhouse.sha256",
                    "browser_download_url": "https://example.invalid/hephaestus-1.2.3-wheelhouse.sha256",
                    "size": 100,
                },
            ]
        }

    def fake_download_asset(
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        if asset.name.endswith(".tar.gz"):
            destination.write_bytes(tar_path.read_bytes())
        else:
            destination.write_text(
                f"{'deadbeef' * 8}  hephaestus-1.2.3-wheelhouse.tar.gz\n",
                encoding="utf-8",
            )
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    with pytest.raises(release.ReleaseError, match="Checksum verification failed"):
        release.download_wheelhouse(
            repository="IAmJonoBo/Hephaestus",
            destination_dir=tmp_path / "downloads",
        )


def test_download_wheelhouse_can_allow_unsigned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tar_path = _make_wheelhouse_tarball(tmp_path)

    def fake_fetch_release(
        repository: str,
        tag: str | None,
        token: str | None,
        *,
        timeout: float,
        max_retries: int,
    ) -> dict[str, Any]:
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
        asset: release.ReleaseAsset,
        destination: Path,
        token: str | None,
        overwrite: bool,
        *,
        timeout: float,
        max_retries: int,
    ) -> Path:
        destination.write_bytes(tar_path.read_bytes())
        return destination

    monkeypatch.setattr(release, "_fetch_release", fake_fetch_release)
    monkeypatch.setattr(release, "_download_asset", fake_download_asset)

    result = release.download_wheelhouse(
        repository="IAmJonoBo/Hephaestus",
        destination_dir=tmp_path / "downloads",
        allow_unsigned=True,
    )

    assert result.archive_path.exists()


def test_validate_github_token_accepts_none() -> None:
    """_validate_github_token allows None for public repos."""
    # Should not raise
    release._validate_github_token(None)


def test_validate_github_token_rejects_empty_string() -> None:
    """_validate_github_token rejects empty token strings."""
    with pytest.raises(release.ReleaseError, match="cannot be empty"):
        release._validate_github_token("")
    
    with pytest.raises(release.ReleaseError, match="cannot be empty"):
        release._validate_github_token("   ")


def test_validate_github_token_accepts_valid_classic_token() -> None:
    """_validate_github_token accepts classic token format."""
    # Should not raise
    release._validate_github_token("ghp_1234567890123456789012345678901234ABCD")


def test_validate_github_token_accepts_valid_pat_token() -> None:
    """_validate_github_token accepts PAT token format."""
    # Should not raise
    release._validate_github_token(
        "github_pat_" + "A" * 82
    )


def test_validate_github_token_warns_on_invalid_format(caplog: pytest.LogCaptureFixture) -> None:
    """_validate_github_token warns for non-matching token patterns."""
    # Invalid format should trigger warning but not raise
    release._validate_github_token("invalid_token_format_12345")
    
    # Check that warning was logged
    assert any("does not match expected patterns" in record.message for record in caplog.records)


def test_fetch_release_validates_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """_fetch_release validates token before making API calls."""
    validation_called = False
    
    def mock_validate(token: str | None) -> None:
        nonlocal validation_called
        validation_called = True
        if token == "":
            raise release.ReleaseError("cannot be empty")
    
    monkeypatch.setattr(release, "_validate_github_token", mock_validate)
    
    # Mock the network call to prevent actual HTTP requests
    def mock_open_with_retries(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Should not reach network call")
    
    monkeypatch.setattr(release, "_open_with_retries", mock_open_with_retries)
    
    # Test that validation is called
    with pytest.raises(release.ReleaseError, match="cannot be empty"):
        release._fetch_release(
            "owner/repo",
            None,
            "",  # Empty token should be rejected by validation
            timeout=10.0,
            max_retries=3,
        )
    
    assert validation_called


def test_fetch_release_handles_401_with_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """_fetch_release provides clear error message for HTTP 401 (expired token)."""
    
    def mock_open_with_retries(*args: Any, **kwargs: Any) -> Any:
        # Simulate HTTP 401 error
        msg = Message()
        msg["Content-Type"] = "application/json"
        raise urllib.error.HTTPError(
            "https://api.github.com/repos/test/repo/releases/latest",
            401,
            "Unauthorized",
            msg,  # type: ignore[arg-type]
            io.BytesIO(b'{"message":"Bad credentials"}'),
        )
    
    monkeypatch.setattr(release, "_open_with_retries", mock_open_with_retries)
    
    with pytest.raises(
        release.ReleaseError,
        match="authentication failed.*expired, invalid, or lack required permissions",
    ):
        release._fetch_release(
            "test/repo",
            None,
            "ghp_fake_token_1234567890123456789012345",
            timeout=10.0,
            max_retries=3,
        )
