from __future__ import annotations

import base64
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from pathlib import Path
from threading import RLock

__all__ = [
    "SERVICE_ACCOUNT_KEYS_ENV",
    "DEFAULT_KEYSTORE_PATH",
    "Role",
    "AuthenticationError",
    "AuthorizationError",
    "ServiceAccountKey",
    "AuthenticatedPrincipal",
    "ServiceAccountKeyStore",
    "ServiceAccountVerifier",
    "generate_service_account_token",
    "get_default_keystore",
    "get_default_verifier",
    "reset_default_verifier",
]

SERVICE_ACCOUNT_KEYS_ENV = "HEPHAESTUS_SERVICE_ACCOUNT_KEYS_PATH"
DEFAULT_KEYSTORE_PATH = Path(".hephaestus/service-accounts.json")


class Role(str, Enum):
    """Supported service-account roles."""

    GUARD_RAILS = "guard-rails"
    CLEANUP = "cleanup"
    ANALYTICS = "analytics"


class AuthenticationError(Exception):
    """Raised when a bearer token fails validation."""


class AuthorizationError(Exception):
    """Raised when a principal lacks the required role."""

    def __init__(self, principal: str, role: str) -> None:
        super().__init__(f"Principal {principal!r} missing required role {role!r}")
        self.principal = principal
        self.role = role


@dataclass(frozen=True)
class ServiceAccountKey:
    """Materialised service-account key definition."""

    key_id: str
    principal: str
    roles: frozenset[str]
    secret: bytes
    expires_at: datetime | None = None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        current = now or datetime.now(UTC)
        return current >= self.expires_at


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Principal extracted from a verified service-account token."""

    principal: str
    roles: frozenset[str]
    key_id: str
    issued_at: datetime
    expires_at: datetime

    def has_role(self, role: str) -> bool:
        return role in self.roles


class ServiceAccountKeyStore:
    """Load and cache service-account key material from disk."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path or DEFAULT_KEYSTORE_PATH)
        self._lock = RLock()
        self._keys: dict[str, ServiceAccountKey] = {}
        self.reload()

    @property
    def path(self) -> Path:
        return self._path

    def reload(self) -> None:
        with self._lock:
            if not self._path.exists():
                self._keys = {}
                return

            data = json.loads(self._path.read_text(encoding="utf-8"))
            keys: dict[str, ServiceAccountKey] = {}
            for entry in data.get("keys", []):
                try:
                    key_id = str(entry["key_id"]).strip()
                    principal = str(entry["principal"]).strip()
                    roles_value = entry.get("roles", [])
                    if not key_id or not principal:
                        raise KeyError("key_id/principal")
                    if not isinstance(roles_value, list) or not roles_value:
                        raise ValueError("roles must be a non-empty list")
                    roles = frozenset(str(role).strip() for role in roles_value)
                    secret_bytes = _b64url_decode(str(entry["secret"]))
                    expires_at_value = entry.get("expires_at")
                    expires_at = (
                        datetime.fromisoformat(expires_at_value).astimezone(UTC)
                        if expires_at_value
                        else None
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    raise AuthenticationError(
                        f"Invalid service-account key definition for entry {entry!r}"
                    ) from exc

                keys[key_id] = ServiceAccountKey(
                    key_id=key_id,
                    principal=principal,
                    roles=roles,
                    secret=secret_bytes,
                    expires_at=expires_at,
                )

            self._keys = keys

    def get(self, key_id: str) -> ServiceAccountKey | None:
        with self._lock:
            return self._keys.get(key_id)

    def all_keys(self) -> list[ServiceAccountKey]:
        with self._lock:
            return list(self._keys.values())


class ServiceAccountVerifier:
    """Verify bearer tokens against a key store."""

    def __init__(self, keystore: ServiceAccountKeyStore) -> None:
        self._keystore = keystore

    def verify_bearer_token(
        self, token: str, *, now: datetime | None = None
    ) -> AuthenticatedPrincipal:
        if not token:
            raise AuthenticationError("Missing bearer token")

        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed bearer token")

        header_raw, payload_raw, signature_raw = parts
        try:
            header = json.loads(_b64url_decode(header_raw))
            payload = json.loads(_b64url_decode(payload_raw))
        except (json.JSONDecodeError, ValueError) as exc:
            raise AuthenticationError("Malformed bearer token payload") from exc

        if header.get("alg") != "HS256":
            raise AuthenticationError("Unsupported token algorithm")

        key_id = header.get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise AuthenticationError("Missing token key identifier")

        key = self._keystore.get(key_id)
        if key is None:
            raise AuthenticationError("Unknown service-account key")

        current_time = now or datetime.now(UTC)
        if key.is_expired(now=current_time):
            raise AuthenticationError("Service-account key expired")

        expected = _sign(f"{header_raw}.{payload_raw}".encode("ascii"), key.secret)
        if not compare_digest(signature_raw, expected):
            raise AuthenticationError("Invalid token signature")

        principal = payload.get("sub")
        if not isinstance(principal, str) or not principal:
            raise AuthenticationError("Token missing subject")

        roles_value = payload.get("roles")
        if not isinstance(roles_value, list) or not roles_value:
            raise AuthenticationError("Token missing roles claim")
        roles = frozenset(str(role) for role in roles_value)
        if not roles.issubset(key.roles):
            raise AuthenticationError("Token asserts roles not granted to key")

        issued_at = _parse_timestamp(payload.get("iat"), field="iat")
        expires_at = _parse_timestamp(payload.get("exp"), field="exp")
        if current_time >= expires_at:
            raise AuthenticationError("Token expired")

        return AuthenticatedPrincipal(
            principal=principal,
            roles=roles,
            key_id=key_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    @staticmethod
    def require_role(principal: AuthenticatedPrincipal, role: str) -> None:
        if not principal.has_role(role):
            raise AuthorizationError(principal.principal, role)

    @staticmethod
    def require_any_role(
        principal: AuthenticatedPrincipal, roles: Iterable[str]
    ) -> None:
        if not any(principal.has_role(role) for role in roles):
            raise AuthorizationError(principal.principal, ",".join(sorted(roles)))


_default_keystore: ServiceAccountKeyStore | None = None
_default_verifier: ServiceAccountVerifier | None = None
_default_lock = RLock()


def get_default_keystore() -> ServiceAccountKeyStore:
    with _default_lock:
        global _default_keystore
        if _default_keystore is None:
            path_value = os.environ.get(SERVICE_ACCOUNT_KEYS_ENV)
            keystore = (
                ServiceAccountKeyStore(Path(path_value))
                if path_value
                else ServiceAccountKeyStore()
            )
            _default_keystore = keystore
        return _default_keystore


def get_default_verifier() -> ServiceAccountVerifier:
    with _default_lock:
        global _default_verifier
        if _default_verifier is None:
            _default_verifier = ServiceAccountVerifier(get_default_keystore())
        return _default_verifier


def reset_default_verifier() -> None:
    with _default_lock:
        global _default_verifier, _default_keystore
        _default_verifier = None
        _default_keystore = None


def generate_service_account_token(
    key: ServiceAccountKey,
    *,
    roles: Iterable[str] | None = None,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    ttl: timedelta | None = None,
) -> str:
    """Generate a signed bearer token for testing or bootstrap flows."""

    issued = (issued_at or datetime.now(UTC)).astimezone(UTC)
    if expires_at is None:
        if ttl is not None:
            expires = issued + ttl
        else:
            expires = issued + timedelta(hours=1)
    else:
        expires = expires_at.astimezone(UTC)

    if expires <= issued:
        raise ValueError("Token expiry must be after issuance time")

    requested_roles = frozenset(roles or key.roles)
    if not requested_roles:
        raise ValueError("Token must include at least one role")
    if not requested_roles.issubset(key.roles):
        missing = ",".join(sorted(requested_roles - key.roles))
        raise ValueError(f"Token requests roles not granted to key: {missing}")

    header = {"alg": "HS256", "typ": "JWT", "kid": key.key_id}
    payload = {
        "sub": key.principal,
        "roles": sorted(requested_roles),
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }

    header_raw = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(f"{header_raw}.{payload_raw}".encode("ascii"), key.secret)
    return f"{header_raw}.{payload_raw}.{signature}"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _sign(payload: bytes, secret: bytes) -> str:
    digest = hmac_new(secret, payload, sha256).digest()
    return _b64url_encode(digest)


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, (int, float)):
        raise AuthenticationError(f"Token missing {field} claim")
    return datetime.fromtimestamp(float(value), tz=UTC)
