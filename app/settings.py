"""Fail-closed server configuration; never include secret values in errors."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    environment: str
    issuer: str
    audience: str
    database_url: str = field(repr=False)
    claim_namespace: str
    anonymous: bool = False
    cors_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls):
        env = os.getenv("APP_ENV", "production")
        bypass = os.getenv("AUTH_DEV_ANONYMOUS", "false")
        if env not in {"production", "development", "test"} or bypass not in {"true", "false"}:
            raise ValueError("Invalid APP_ENV or AUTH_DEV_ANONYMOUS")
        anonymous = bypass == "true"
        if anonymous and env != "development":
            raise ValueError("Anonymous access is permitted only in development")
        issuer = os.getenv("AUTH0_ISSUER", "")
        audience = os.getenv("AUTH0_AUDIENCE", "")
        database = os.getenv("DATABASE_URL", "")
        namespace = os.getenv("AUTH0_CLAIM_NAMESPACE", "")
        if not anonymous:
            for name, value in (("AUTH0_ISSUER", issuer), ("AUTH0_CLAIM_NAMESPACE", namespace)):
                parsed = urlsplit(value)
                if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                        or parsed.password or parsed.query or parsed.fragment or not value.endswith("/")):
                    raise ValueError(f"{name} must be an HTTPS URL ending in /")
            if not audience or audience.strip() != audience:
                raise ValueError("AUTH0_AUDIENCE is required")
            try:
                url = make_url(database)
                if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.host or not url.database:
                    raise ValueError()
                if env == "production" and url.query.get("sslmode") != "verify-full":
                    raise ValueError()
            except Exception:
                raise ValueError("DATABASE_URL must use PostgreSQL; production requires sslmode=verify-full") from None
        origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip())
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in ({"https"} if env == "production" else {"http", "https"})
                    or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or "*" in origin):
                raise ValueError("CORS_ORIGINS must contain exact origins")
        return cls(env, issuer, audience, database, namespace, anonymous, origins)
