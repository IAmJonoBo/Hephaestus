"""Unit tests for service-account authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hephaestus.api import auth


def _write_keystore(
    path: Path, *, key_id: str, principal: str, roles: set[str], secret: bytes
) -> None:
    payload = {
        "keys": [
            {
                "key_id": key_id,
                "principal": principal,
                "roles": sorted(roles),
                "secret": base64.urlsafe_b64encode(secret).decode("ascii"),
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_generate_and_verify_token_success(tmp_path: Path) -> None:
    secret = b"a" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="key-1",
        principal="svc@example.com",
        roles={auth.Role.GUARD_RAILS.value, auth.Role.CLEANUP.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)

    key = keystore.get("key-1")
    assert key is not None

    token = auth.generate_service_account_token(
        key,
        roles={auth.Role.GUARD_RAILS.value},
        issued_at=datetime.now(UTC) - timedelta(seconds=1),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    principal = verifier.verify_bearer_token(token)
    assert principal.principal == "svc@example.com"
    assert auth.Role.GUARD_RAILS.value in principal.roles
    assert principal.key_id == "key-1"


def test_service_account_key_expiration_helpers() -> None:
    now = datetime.now(UTC)
    key = auth.ServiceAccountKey(
        key_id="expiring",
        principal="svc-expiring@example.com",
        roles=frozenset({auth.Role.GUARD_RAILS.value}),
        secret=b"z" * 32,
        expires_at=now + timedelta(seconds=30),
    )

    assert key.is_expired(now=now) is False
    assert key.is_expired(now=now + timedelta(minutes=1)) is True


def test_verify_token_expired(tmp_path: Path) -> None:
    secret = b"b" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="expired",
        principal="svc-expired@example.com",
        roles={auth.Role.CLEANUP.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("expired")
    assert key is not None

    issued = datetime.now(UTC) - timedelta(minutes=5)
    token = auth.generate_service_account_token(
        key,
        issued_at=issued,
        expires_at=issued + timedelta(minutes=1),
    )

    with pytest.raises(auth.AuthenticationError):
        verifier.verify_bearer_token(token)


def test_verify_token_invalid_signature(tmp_path: Path) -> None:
    secret = b"c" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="sig",
        principal="svc-sig@example.com",
        roles={auth.Role.ANALYTICS.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("sig")
    assert key is not None

    token = auth.generate_service_account_token(key)
    header, payload, signature = token.split(".")
    tampered_signature = signature[:-1] + ("A" if signature[-1] != "A" else "B")

    with pytest.raises(auth.AuthenticationError):
        verifier.verify_bearer_token(f"{header}.{payload}.{tampered_signature}")


def test_require_role_enforces_membership(tmp_path: Path) -> None:
    secret = b"d" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="role",
        principal="svc-role@example.com",
        roles={auth.Role.CLEANUP.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("role")
    assert key is not None

    token = auth.generate_service_account_token(key)
    principal = verifier.verify_bearer_token(token)

    with pytest.raises(auth.AuthorizationError):
        auth.ServiceAccountVerifier.require_role(principal, auth.Role.ANALYTICS.value)


def test_keystore_reload_detects_new_keys(tmp_path: Path) -> None:
    keystore_path = tmp_path / "keys.json"
    keystore_path.write_text(json.dumps({"keys": []}), encoding="utf-8")

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    assert keystore.get("dynamic") is None

    payload = {
        "keys": [
            {
                "key_id": "dynamic",
                "principal": "svc-dynamic@example.com",
                "roles": [auth.Role.ANALYTICS.value],
                "secret": base64.urlsafe_b64encode(b"e" * 32).decode("ascii"),
            }
        ]
    }
    keystore_path.write_text(json.dumps(payload), encoding="utf-8")

    keystore.reload()

    key = keystore.get("dynamic")
    assert key is not None
    assert key.principal == "svc-dynamic@example.com"


def test_require_any_role_checks_subset(tmp_path: Path) -> None:
    secret = b"f" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="combo",
        principal="svc-combo@example.com",
        roles={auth.Role.GUARD_RAILS.value, auth.Role.CLEANUP.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("combo")
    assert key is not None

    token = auth.generate_service_account_token(key, roles={auth.Role.GUARD_RAILS.value})
    principal = verifier.verify_bearer_token(token)

    auth.ServiceAccountVerifier.require_any_role(
        principal, [auth.Role.GUARD_RAILS.value, auth.Role.ANALYTICS.value]
    )

    with pytest.raises(auth.AuthorizationError):
        auth.ServiceAccountVerifier.require_any_role(principal, [auth.Role.ANALYTICS.value])


def test_generate_service_account_token_rejects_unknown_role(tmp_path: Path) -> None:
    secret = b"g" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="limited",
        principal="svc-limited@example.com",
        roles={auth.Role.CLEANUP.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    key = keystore.get("limited")
    assert key is not None

    with pytest.raises(ValueError):
        auth.generate_service_account_token(
            key,
            roles={auth.Role.ANALYTICS.value},
        )


def test_verify_token_unknown_key(tmp_path: Path) -> None:
    keystore_path = tmp_path / "keys.json"
    keystore_path.write_text(json.dumps({"keys": []}), encoding="utf-8")

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)

    ephemeral_key = auth.ServiceAccountKey(
        key_id="ghost",
        principal="ghost@example.com",
        roles=frozenset({auth.Role.GUARD_RAILS.value}),
        secret=b"h" * 32,
    )
    token = auth.generate_service_account_token(ephemeral_key)

    with pytest.raises(auth.AuthenticationError):
        verifier.verify_bearer_token(token)


def test_verify_token_rejects_unsupported_algorithm(tmp_path: Path) -> None:
    secret = b"i" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="alg",
        principal="svc-alg@example.com",
        roles={auth.Role.GUARD_RAILS.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("alg")
    assert key is not None

    token = auth.generate_service_account_token(key)
    header_raw, payload_raw, _ = token.split(".")

    bad_header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": key.key_id,
    }
    bad_header_raw = (
        base64.urlsafe_b64encode(json.dumps(bad_header, separators=(",", ":")).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )

    message = f"{bad_header_raw}.{payload_raw}".encode("ascii")
    signature = (
        base64.urlsafe_b64encode(hmac.new(secret, message, hashlib.sha256).digest())
        .rstrip(b"=")
        .decode("ascii")
    )

    with pytest.raises(auth.AuthenticationError):
        verifier.verify_bearer_token(f"{bad_header_raw}.{payload_raw}.{signature}")


def test_verify_token_missing_timestamp_claims(tmp_path: Path) -> None:
    secret = b"j" * 32
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="iat",
        principal="svc-iat@example.com",
        roles={auth.Role.GUARD_RAILS.value},
        secret=secret,
    )

    keystore = auth.ServiceAccountKeyStore(keystore_path)
    verifier = auth.ServiceAccountVerifier(keystore)
    key = keystore.get("iat")
    assert key is not None

    token = auth.generate_service_account_token(key)
    header_raw, payload_raw, _ = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(payload_raw + "=" * (-len(payload_raw) % 4)))
    payload["iat"] = "invalid"

    tampered_payload_raw = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )

    message = f"{header_raw}.{tampered_payload_raw}".encode("ascii")
    signature = (
        base64.urlsafe_b64encode(hmac.new(secret, message, hashlib.sha256).digest())
        .rstrip(b"=")
        .decode("ascii")
    )

    with pytest.raises(auth.AuthenticationError):
        verifier.verify_bearer_token(f"{header_raw}.{tampered_payload_raw}.{signature}")


def test_keystore_rejects_invalid_entries(tmp_path: Path) -> None:
    keystore_path = tmp_path / "keys.json"
    keystore_path.write_text(
        json.dumps(
            {
                "keys": [
                    {
                        "key_id": "",
                        "principal": "svc-invalid@example.com",
                        "roles": [],
                        "secret": "not-base64",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(auth.AuthenticationError):
        auth.ServiceAccountKeyStore(keystore_path)


def test_default_verifier_uses_environment_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    keystore_path = tmp_path / "keys.json"
    _write_keystore(
        keystore_path,
        key_id="default",
        principal="svc-default@example.com",
        roles={auth.Role.GUARD_RAILS.value},
        secret=b"k" * 32,
    )

    monkeypatch.setenv(auth.SERVICE_ACCOUNT_KEYS_ENV, str(keystore_path))
    auth.reset_default_verifier()

    try:
        verifier = auth.get_default_verifier()
        token = auth.generate_service_account_token(
            auth.ServiceAccountKey(
                key_id="default",
                principal="svc-default@example.com",
                roles=frozenset({auth.Role.GUARD_RAILS.value}),
                secret=b"k" * 32,
            )
        )
        principal = verifier.verify_bearer_token(token)
        assert principal.principal == "svc-default@example.com"
    finally:
        auth.reset_default_verifier()
