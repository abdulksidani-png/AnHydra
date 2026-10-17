from datetime import datetime, timezone
import json
import logging
from unittest.mock import Mock, patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import jwt
import pytest

from app.auth import KeyCache, TokenVerifier
from app.database import UserStore
from app.logging_safety import RedactCredentials
from app.main import ConfiguredCORS, app, lifespan
from app.settings import Settings
from sqlalchemy.exc import OperationalError

ISSUER = "https://tenant.example/"
NS = "https://anhydra.work/claims/"
SETTINGS = Settings("test", ISSUER, "anhydra-api", "postgresql://localhost/test", NS)


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwk(key, kid="one"):
    return {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": kid, "alg": "RS256"}


def token(key, **changes):
    claims = dict(iss=ISSUER, sub="Exact|Subject", aud="anhydra-api",
                  exp=datetime.now(timezone.utc).timestamp() + 300,
                  **{NS + "token_kind": "user_access", NS + "admission": "google"})
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "one"})


@pytest.fixture
def api(key):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": [jwk(key)]})))
    previous = app.state._state.copy()
    app.state.settings = SETTINGS
    app.state.verifier = TokenVerifier(SETTINGS, KeyCache(ISSUER, client))
    app.state.users = Mock()
    app.state.users.resolve.return_value = dict(id=uuid4(), display_name=None, email=None,
        email_verified=False, created_at=datetime.now(timezone.utc))
    try:
        yield TestClient(app)
    finally:
        app.state._state.clear()
        app.state._state.update(previous)
        client.close()


def test_me_shape_and_signed_identity(api, key):
    response = api.get("/me", headers={"Authorization": "Bearer " + token(key, email="untrusted@example.edu", role="admin")})
    assert response.status_code == 200
    assert set(response.json()) == {"id", "display_name", "email", "email_verified", "created_at"}
    assert response.json()["email"] is None
    assert response.json()["email_verified"] is False
    app.state.users.resolve.assert_called_once_with(ISSUER, "Exact|Subject")


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer abc", "Bearer a.b.c", "Bearer  a.b.c", "Bearer a.b.c extra"])
def test_missing_malformed_credentials(api, header):
    response = api.post("/score", json={"sequence": "A" * 40}, headers={} if header is None else {"Authorization": header})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    app.state.users.resolve.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"iss": "https://wrong.example/"}, {"aud": "spa-client-id"}, {"exp": 1},
    {"nbf": 9999999999}, {"sub": ""}, {"sub": None},
    {NS + "token_kind": None}, {NS + "token_kind": "id_token"},
    {"gty": "client-credentials"},
])
def test_invalid_claims(api, key, changes):
    response = api.get("/me", headers={"Authorization": "Bearer " + token(key, **changes)})
    assert response.status_code == 401
    app.state.users.resolve.assert_not_called()


@pytest.mark.parametrize("claim", ["iss", "sub", "aud", "exp"])
def test_missing_required_claim(api, key, claim):
    claims = jwt.decode(token(key), options={"verify_signature": False})
    claims.pop(claim)
    encoded = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "one"})
    assert api.get("/me", headers={"Authorization": "Bearer " + encoded}).status_code == 401


def test_bad_signature_and_algorithm(api, key):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for encoded in (token(other), jwt.encode({"sub": "x"}, "a" * 32, algorithm="HS256", headers={"kid": "one"})):
        assert api.get("/me", headers={"Authorization": "Bearer " + encoded}).status_code == 401


def test_token_supplied_key_url_is_ignored(api, key):
    claims = jwt.decode(token(key), options={"verify_signature": False})
    encoded = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "one", "jku": "https://attacker.example/keys"})
    with patch.object(app.state.verifier.keys.client, "get", wraps=app.state.verifier.keys.client.get) as get:
        assert api.get("/me", headers={"Authorization": "Bearer " + encoded}).status_code == 200
    get.assert_called_once_with(ISSUER + ".well-known/jwks.json")


def test_verified_institution_admission(api, key):
    assert api.get("/me", headers={"Authorization": "Bearer " + token(key, **{NS + "admission": "verified_edu"})}).status_code == 200


def test_duplicate_authorization(api, key):
    headers = [("Authorization", "Bearer " + token(key))] * 2
    assert api.get("/me", headers=headers).status_code == 401


@pytest.mark.parametrize("admission", [None, False, "microsoft", "edu", "admin"])
def test_admission_before_inference(api, key, admission):
    with patch("app.main.predict") as predict:
        response = api.post("/score", json={"sequence": "A" * 40},
            headers={"Authorization": "Bearer " + token(key, **{NS + "admission": admission})})
    assert response.status_code == 403
    predict.assert_not_called()
    app.state.users.resolve.assert_not_called()


def test_disabled_before_inference(api, key):
    app.state.users.resolve.side_effect = HTTPException(403, "This account is disabled.")
    with patch("app.main.predict") as predict:
        assert api.post("/score", json={"sequence": "A" * 40},
            headers={"Authorization": "Bearer " + token(key)}).status_code == 403
    predict.assert_not_called()


def test_keys_rotation_throttle_and_outage(key):
    calls = []
    body = {"keys": [jwk(key)]}
    def fetch(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=body)
    with httpx.Client(transport=httpx.MockTransport(fetch)) as client, patch("app.auth.time.monotonic", return_value=100) as clock:
        cache = KeyCache(ISSUER, client)
        cache.get("one")
        cache.get("one")
        for _ in range(10):
            with pytest.raises(HTTPException) as exc:
                cache.get("unknown")
            assert exc.value.status_code == 401
        assert len(calls) == 1
        body["keys"].append(jwk(key, "two"))
        clock.return_value = 131
        cache.get("two")
        assert calls == [ISSUER + ".well-known/jwks.json"] * 2
        body.clear()  # Invalid/unavailable key service, safely fail closed.
        clock.return_value = 162
        with pytest.raises(HTTPException) as exc:
            cache.get("three")
        assert exc.value.status_code == 503
        cache.get("one")  # A still-fresh known key remains usable.
        clock.return_value = 4000
        with pytest.raises(HTTPException) as exc:
            cache.get("one")
        assert exc.value.status_code == 503


def test_key_network_outage(api, key):
    app.state.verifier.keys.client = Mock()
    app.state.verifier.keys.client.get.side_effect = httpx.ConnectError("private infrastructure")
    response = api.get("/me", headers={"Authorization": "Bearer " + token(key)})
    assert response.status_code == 503
    assert "private" not in response.text
    app.state.users.resolve.assert_not_called()


def test_database_outage_is_safe():
    engine = Mock()
    engine.begin.side_effect = OperationalError("secret database", {}, Exception("secret"))
    with pytest.raises(HTTPException) as exc:
        UserStore(engine).resolve(ISSUER, "user")
    assert exc.value.status_code == 503
    assert "secret" not in exc.value.detail


def set_config(monkeypatch):
    for name, value in {"APP_ENV": "production", "AUTH_DEV_ANONYMOUS": "false", "AUTH0_ISSUER": ISSUER,
                        "AUTH0_AUDIENCE": "anhydra-api", "AUTH0_CLAIM_NAMESPACE": NS,
                        "DATABASE_URL": "postgresql://user:secret@localhost/test?sslmode=verify-full",
                        "CORS_ORIGINS": "https://anhydra.work"}.items():
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize("field", ["AUTH0_ISSUER", "AUTH0_AUDIENCE", "AUTH0_CLAIM_NAMESPACE", "DATABASE_URL"])
def test_missing_production_configuration(monkeypatch, field):
    set_config(monkeypatch)
    monkeypatch.delenv(field)
    with pytest.raises(ValueError), TestClient(FastAPI(lifespan=lifespan)):
        pass


def test_config_bypass_and_tls(monkeypatch):
    set_config(monkeypatch)
    assert Settings.from_env().environment == "production"
    monkeypatch.setenv("AUTH_DEV_ANONYMOUS", "true")
    with pytest.raises(ValueError):
        Settings.from_env()
    monkeypatch.setenv("APP_ENV", "development")
    assert Settings.from_env().anonymous
    set_config(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    with pytest.raises(ValueError):
        Settings.from_env()


@pytest.mark.parametrize("field,value", [("APP_ENV", "prod"), ("AUTH_DEV_ANONYMOUS", "1"),
    ("AUTH0_ISSUER", "http://tenant.example/"), ("AUTH0_ISSUER", "https://tenant.example"),
    ("AUTH0_ISSUER", "https://tenant.example/?query=x"), ("DATABASE_URL", "sqlite:///users.db"),
    ("CORS_ORIGINS", "*"), ("CORS_ORIGINS", "https://app.example/path"),
    ("CORS_ORIGINS", "http://app.example")])
def test_invalid_configuration(monkeypatch, field, value):
    set_config(monkeypatch)
    monkeypatch.setenv(field, value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_exact_cors_and_development_startup(monkeypatch):
    set_config(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_DEV_ANONYMOUS", "true")
    instance = FastAPI(lifespan=lifespan)
    instance.add_middleware(ConfiguredCORS)
    with TestClient(instance) as client:
        assert instance.state.settings.anonymous
        headers = {"Origin": "https://anhydra.work", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "Authorization,Content-Type"}
        response = client.options("/score", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://anhydra.work"
        headers["Origin"] = "https://evil.example"
        response = client.options("/score", headers=headers)
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_public_health(api):
    assert api.get("/health").status_code == 200


def test_log_redaction(key):
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s %s %s %s %s',
        ("client", "GET", "/me?access_token=secret", "HTTP/1.1", 200), None)
    RedactCredentials().filter(record)
    assert "secret" not in record.getMessage()
    record = logging.LogRecord("app", logging.INFO, "", 0, "Bearer %s", (token(key),), None)
    RedactCredentials().filter(record)
    assert record.getMessage() == "Bearer [REDACTED]"
