"""Actual TS clients through Vite and FastAPI, with real PostgreSQL user storage.

Controlled RSA keys replace the external tenant; only ML inference is stubbed.
No real Auth0 login or trained model is required or claimed by this test.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
import httpx
import jwt
import pytest
from sqlalchemy import text
import uvicorn

from app import main
from app.auth import KeyCache, TokenVerifier
from app.database import UserStore
from app.settings import Settings


def test_frontend_proxy_and_backend_contract(database, monkeypatch, tmp_path):
    frontend = Path(__file__).resolve().parents[1] / "frontend" / "anhydra-frontend"
    node = shutil.which("node")
    if not node or not (frontend / "node_modules" / "typescript").exists():
        pytest.skip("Run npm ci in frontend/anhydra-frontend and install Node for HTTP integration")
    issuer, namespace = "https://integration.invalid/", "https://anhydra.work/claims/"
    settings = Settings("test", issuer, "integration-api", "", namespace)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "integration"}
    def mint(subject="integration-user", **changes):
        claims = {"iss": issuer, "sub": subject, "aud": settings.audience,
                  "exp": datetime.now(timezone.utc).timestamp() + 300,
                  namespace + "token_kind": "user_access", namespace + "admission": "google"}
        claims.update(changes)
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "integration"})
    store = UserStore(database)
    disabled = store.resolve(issuer, "disabled")
    with database.begin() as conn:
        conn.execute(text("UPDATE app_users SET status='disabled' WHERE id=:id"), disabled)
    model_file = tmp_path / "fixture-model"
    model_file.touch()
    predict = Mock(return_value=SimpleNamespace(score=.7, label="protective", nearest_homolog=None, top_features=[]))
    monkeypatch.setattr(main, "MODELS_PATH", model_file)
    monkeypatch.setattr(main, "predict", predict)
    monkeypatch.setattr(main, "explain", lambda *args: "Controlled integration fixture")

    @asynccontextmanager
    async def lifespan(application):
        with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"keys": [jwk]}))) as client:
            application.state.settings = settings
            application.state.verifier = TokenVerifier(settings, KeyCache(issuer, client))
            application.state.users = store
            yield

    application = FastAPI(lifespan=lifespan)
    # Reuse production route handlers and dependencies, with isolated service resources.
    application.router.routes = main.app.router.routes.copy()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(application, log_level="error", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(.05)
            assert server.started, "Integration backend failed to start"
            payload = {"backend": f"http://127.0.0.1:{port}", "tokens": {
                "valid": mint(), "expired": mint(exp=1),
                "denied": mint(**{namespace + "admission": "not-admitted"}),
                "disabled": mint("disabled")}}
            result = subprocess.run([node, "tests/backend-integration.cjs"], cwd=frontend,
                input=json.dumps(payload), text=True, capture_output=True, timeout=60)
            assert result.returncode == 0, result.stdout + result.stderr
            predict.assert_called_once_with("A" * 40)
            with database.connect() as conn:
                assert conn.scalar(text("SELECT count(*) FROM app_users")) == 2
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "Integration server did not shut down"
