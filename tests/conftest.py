import pytest


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
