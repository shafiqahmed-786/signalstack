from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass

import jwt
import structlog
from jwt import PyJWKClient, InvalidTokenError, DecodeError
from jwt.exceptions import PyJWKClientError

from app.config import get_settings

log = structlog.get_logger(__name__)

# Role mapping: Clerk's org role labels → our internal role names
CLERK_ROLE_MAP: dict[str, str] = {
    "org:admin": "admin",
    "org:member": "analyst",
}

WEBHOOK_TOLERANCE_SECONDS = 300  # 5-minute replay protection window


@dataclass(frozen=True)
class ClerkClaims:
    """
    Decoded and validated claims from a Clerk-issued JWT.

    sub      = Clerk user ID (e.g., "user_2abc...")
    org_id   = Clerk organization ID (e.g., "org_2abc..."). None if the user
               made a request without an active org context.
    org_role = Clerk role label (e.g., "org:admin", "org:member").
    """

    user_id: str            # sub claim
    org_id: str | None      # org_id claim
    org_role: str | None    # org_role claim
    session_id: str         # sid claim
    issued_at: int
    expires_at: int

    @property
    def internal_role(self) -> str:
        """Map Clerk role to our internal role string."""
        return CLERK_ROLE_MAP.get(self.org_role or "", "analyst")


class ClerkJWTVerifier:
    """
    Verifies Clerk-issued JWTs using the public keys from Clerk's JWKS endpoint.

    PyJWKClient handles:
      - Fetching the JWKS on first use
      - Caching keys in memory (lifespan=300s)
      - Selecting the correct key by kid header
      - Re-fetching on unknown kid (handles key rotation)
    """

    def __init__(self, jwks_url: str) -> None:
        self._jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            lifespan=300,  # Refresh JWKS every 5 minutes
            headers={"User-Agent": "klypup-backend/0.1.0"},
        )
        log.info("clerk.verifier_initialized", jwks_url=jwks_url)

    def verify(self, token: str) -> ClerkClaims:
        """
        Verify a Bearer token and return typed claims.
        Raises ValueError with a human-readable message on any failure.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        except (PyJWKClientError, Exception) as exc:
            log.warning("clerk.jwks_key_fetch_failed", error=str(exc))
            raise ValueError(f"Could not fetch signing key: {exc}") from exc

        try:
            payload: dict = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={
                    "verify_aud": False,   # Clerk does not set standard aud
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                },
            )
        except (DecodeError, InvalidTokenError) as exc:
            log.warning("clerk.jwt_decode_failed", error=str(exc))
            raise ValueError(f"JWT verification failed: {exc}") from exc

        return ClerkClaims(
            user_id=payload["sub"],
            org_id=payload.get("org_id"),
            org_role=payload.get("org_role"),
            session_id=payload.get("sid", ""),
            issued_at=int(payload.get("iat", 0)),
            expires_at=int(payload.get("exp", 0)),
        )


# ── Webhook signature verification ────────────────────────────────────────────


def verify_webhook_signature(
    payload_bytes: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    webhook_secret: str,
) -> bool:
    """
    Verify a Clerk webhook payload using Svix's signature scheme.

    Svix uses HMAC-SHA256 over: "{svix-id}.{svix-timestamp}.{raw-body}"
    The secret is base64-encoded after the "whsec_" prefix.

    Returns True if the signature is valid and the timestamp is within
    the WEBHOOK_TOLERANCE_SECONDS window (replay protection).
    """
    # 1. Timestamp replay protection
    try:
        ts = int(svix_timestamp)
    except (ValueError, TypeError):
        log.warning("webhook.invalid_timestamp", svix_timestamp=svix_timestamp)
        return False

    now = int(time.time())
    if abs(now - ts) > WEBHOOK_TOLERANCE_SECONDS:
        log.warning(
            "webhook.timestamp_out_of_tolerance",
            svix_timestamp=ts,
            now=now,
            delta=abs(now - ts),
        )
        return False

    # 2. Decode the webhook secret
    try:
        secret_bytes = base64.b64decode(webhook_secret.removeprefix("whsec_"))
    except Exception as exc:
        log.error("webhook.secret_decode_failed", error=str(exc))
        return False

    # 3. Build signed content string
    signed_content = f"{svix_id}.{svix_timestamp}.{payload_bytes.decode('utf-8')}"

    # 4. Compute HMAC-SHA256
    computed_digest = hmac.new(
        secret_bytes,
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed_b64 = base64.b64encode(computed_digest).decode("utf-8")

    # 5. Compare against each provided signature (Svix can send multiple)
    # Signature format: "v1,<base64>" — may be comma-separated for multiple signatures
    provided_signatures = [
        sig.removeprefix("v1,") for sig in svix_signature.split(" ")
        if sig.startswith("v1,")
    ]

    if not provided_signatures:
        log.warning("webhook.no_valid_signature_format", svix_signature=svix_signature)
        return False

    return any(
        hmac.compare_digest(computed_b64, sig) for sig in provided_signatures
    )


# ── Module-level singleton ────────────────────────────────────────────────────


_verifier_instance: ClerkJWTVerifier | None = None


def get_clerk_verifier() -> ClerkJWTVerifier:
    """
    Returns the module-level ClerkJWTVerifier singleton.
    Initialized lazily on first call (safe for testing — can mock get_settings).
    """
    global _verifier_instance
    if _verifier_instance is None:
        settings = get_settings()
        _verifier_instance = ClerkJWTVerifier(jwks_url=settings.clerk_jwks_url)
    return _verifier_instance