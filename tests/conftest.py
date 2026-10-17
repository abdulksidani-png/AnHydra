import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text

from app.database import database_engine


@pytest.fixture
def authorized_app():
    """Only inference regression tests bypass auth; auth tests exercise real verification."""
    from app.auth import authenticated_user
    from app.main import app
    app.dependency_overrides[authenticated_user] = lambda: {"id": "test-user"}
    try:
        yield app
    finally:
        app.dependency_overrides.pop(authenticated_user, None)


@pytest.fixture
def database(monkeypatch):
    """A unique, migrated schema on an explicitly supplied disposable database."""
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
