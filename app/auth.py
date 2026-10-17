"""Trusted-issuer JWT verification and the shared admission dependency."""
from datetime import datetime, timezone
import re
import threading
import time
from uuid import UUID

import httpx
import jwt
from fastapi import HTTPException, Request


def unauthorized():
    return HTTPException(401, "Missing or invalid access token.", headers={"WWW-Authenticate": "Bearer"})


class KeyCache:
    """Per-worker cache, one refresh per 30s at most, 1h maximum key age.

    Failed refreshes never extend the lifetime of cached keys. The lock also
    bounds simultaneous attacker-controlled unknown-kid refresh requests.
    """
    def __init__(self, issuer, client):
        self.url = issuer + ".well-known/jwks.json"
        self.client = client
        self.keys = {}
        self.expires = 0.
        self.retry_at = 0.
        self.failed = False
        self.lock = threading.Lock()

    def get(self, kid):
        with self.lock:
            now = time.monotonic()
            if now < self.expires and kid in self.keys:
                return self.keys[kid]
            if now >= self.retry_at:
                self.retry_at = now + 30
                try:
                    response = self.client.get(self.url)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict) or not isinstance(data.get("keys"), list) or len(data["keys"]) > 100:
                        raise ValueError("Invalid key set")
                    keys = {}
                    for item in data["keys"]:
                        if not isinstance(item, dict):
                            raise ValueError("Invalid signing key")
                        if (item.get("kty") == "RSA" and item.get("use", "sig") == "sig"
                                and item.get("alg", "RS256") == "RS256"
                                and "verify" in item.get("key_ops", ["verify"])):
                            name = item["kid"]
                            if not isinstance(name, str) or name in keys:
                                raise ValueError("Invalid key identifiers")
                            keys[name] = jwt.PyJWK.from_dict(item, algorithm="RS256").key
                    if not keys:
                        raise ValueError("Empty signing key set")
                    self.keys, self.expires, self.failed = keys, now + 3600, False
                except (httpx.HTTPError, ValueError, KeyError, TypeError, jwt.PyJWTError):
                    self.failed = True
            if self.failed or now >= self.expires:
                raise HTTPException(503, "Identity verification is temporarily unavailable.")
            if kid not in self.keys:
                raise unauthorized()
            return self.keys[kid]


class TokenVerifier:
    def __init__(self, settings, keys):
        self.settings, self.keys = settings, keys

    def verify(self, token):
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid or len(kid) > 256:
                raise unauthorized()
            claims = jwt.decode(token, self.keys.get(kid), algorithms=["RS256"],
                                issuer=self.settings.issuer, audience=self.settings.audience,
                                options={"require": ["iss", "sub", "aud", "exp"]})
            # Exact comparison also guards against library issuer matching changes.
            if claims["iss"] != self.settings.issuer or not isinstance(claims["sub"], str) or not claims["sub"]:
                raise unauthorized()
            ns = self.settings.claim_namespace
            if claims.get(ns + "token_kind") != "user_access" or claims.get("gty") == "client-credentials":
                raise unauthorized()
            if claims.get(ns + "admission") not in ("google", "verified_edu"):
                raise HTTPException(403, "This account is not eligible for access.")
            return claims
        except (jwt.PyJWTError, ValueError, TypeError):
            raise unauthorized() from None


def authenticated_user(request: Request):
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise HTTPException(503, "Authentication is unavailable.")
    if settings.anonymous:
        return dict(id=UUID("00000000-0000-0000-0000-000000000001"), display_name=None,
                    email=None, email_verified=False, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    headers = request.headers.getlist("authorization")
    if len(headers) != 1 or len(headers[0]) > 16384:
        raise unauthorized()
    match = re.fullmatch(r"Bearer ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", headers[0], re.IGNORECASE)
    if not match:
        raise unauthorized()
    claims = request.app.state.verifier.verify(match.group(1))
    return request.app.state.users.resolve(claims["iss"], claims["sub"])
