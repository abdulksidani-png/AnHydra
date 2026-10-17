"""Real PostgreSQL integration checks; CI supplies a disposable database.

TEST_DATABASE_URL must point to a disposable database with schema-create rights.
Each test gets a unique schema; no existing tables are touched.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import threading
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import HTTPException
import pytest
from sqlalchemy import event, text

from app.database import UserStore, database_engine


@pytest.fixture
def database(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for real PostgreSQL tests")
    schema = "auth_test_" + uuid4().hex
    admin = database_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    from sqlalchemy.engine import make_url
    isolated = make_url(url).update_query_dict({"options": f"-c search_path={schema}"})
    # database_engine sets bounded timeouts while preserving the requested test schema.
    isolated_url = isolated.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", isolated_url)
    engine = database_engine(isolated_url)
    try:
        command.upgrade(Config("alembic.ini"), "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_first_repeat_exact_identity_and_nullable_profile(database):
    store = UserStore(database)
    first = store.resolve("https://issuer/", "Provider|Case")
    assert first == store.resolve("https://issuer/", "Provider|Case")
    assert first["display_name"] is first["email"] is None
    assert first["email_verified"] is False
    assert first["created_at"].utcoffset().total_seconds() == 0
    second = store.resolve("https://issuer/", "Provider|case")
    third = store.resolve("https://other-issuer/", "Provider|Case")
    assert len({first["id"], second["id"], third["id"]}) == 3
    with database.begin() as conn:
        conn.execute(text("UPDATE app_users SET email='same@example.edu', email_verified=true"))
    assert store.resolve("https://issuer/", "Provider|Case")["id"] == first["id"]
    assert store.resolve("https://issuer/", "Provider|case")["id"] == second["id"]


def test_concurrent_first_requests_rollback_losing_users(database):
    barrier = threading.Barrier(6)
    local = threading.local()
    def after_lookup(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT u.*") and not getattr(local, "seen", False):
            local.seen = True
            barrier.wait(timeout=15)
    event.listen(database, "after_cursor_execute", after_lookup)
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(lambda _: UserStore(database).resolve("https://issuer/", "concurrent"), range(6)))
    finally:
        event.remove(database, "after_cursor_execute", after_lookup)
    assert len({row["id"] for row in rows}) == 1
    with database.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM app_users")) == 1
        assert conn.scalar(text("SELECT count(*) FROM auth_identities")) == 1


def test_status_rechecked_and_last_seen_throttled(database):
    store = UserStore(database)
    user = store.resolve("https://issuer/", "user")
    with database.connect() as conn:
        seen = conn.scalar(text("SELECT last_seen_at FROM app_users"))
    store.resolve("https://issuer/", "user")
    with database.begin() as conn:
        assert conn.scalar(text("SELECT last_seen_at FROM app_users")) == seen
        conn.execute(text("UPDATE app_users SET last_seen_at=now()-interval '1 hour'"))
    store.resolve("https://issuer/", "user")
    with database.begin() as conn:
        assert conn.scalar(text("SELECT last_seen_at FROM app_users")) > seen
        conn.execute(text("UPDATE app_users SET status='disabled', updated_at=now() WHERE id=:id"), user)
    with pytest.raises(HTTPException) as exc:
        store.resolve("https://issuer/", "user")
    assert exc.value.status_code == 403


def test_delete_cascades_identity(database):
    UserStore(database).resolve("https://issuer/", "user")
    with database.begin() as conn:
        conn.execute(text("DELETE FROM app_users"))
        assert conn.scalar(text("SELECT count(*) FROM auth_identities")) == 0
