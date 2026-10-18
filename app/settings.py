"""Fail-closed server configuration; never include secret values in errors."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

# A database on the same machine is reached over the loopback interface, which never leaves the
# host, so TLS adds nothing there. Every other host still requires sslmode=verify-full.
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# libpq/psycopg let these query parameters override where the connection actually goes, so a URL
# carrying any of them is never treated as loopback, whatever its visible host says.
CONNECTION_TARGET_OVERRIDES = frozenset({"host", "hostaddr", "service", "port"})


def is_loopback_database(url):
    return url.host in LOOPBACK_HOSTS and not CONNECTION_TARGET_OVERRIDES & set(url.query)


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
        public = os.getenv("PUBLIC_ACCESS", "false")
        if (env not in {"production", "development", "test"} or bypass not in {"true", "false"}
                or public not in {"true", "false"}):
            raise ValueError("Invalid APP_ENV, AUTH_DEV_ANONYMOUS or PUBLIC_ACCESS")
        if bypass == "true" and env != "development":
            raise ValueError("Anonymous access is permitted only in development")
        # PUBLIC_ACCESS is the deliberate production choice to run without sign-in: /score is open
        # to everyone, and Auth0 and the account database are neither configured nor contacted.
        anonymous = bypass == "true" or public == "true"
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
                if (env == "production" and url.query.get("sslmode") != "verify-full"
                        and not is_loopback_database(url)):
                    raise ValueError()
            except Exception:
                raise ValueError("DATABASE_URL must use PostgreSQL; production requires "
                                 "sslmode=verify-full unless the database is on localhost") from None
        origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip())
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in ({"https"} if env == "production" else {"http", "https"})
                    or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or "*" in origin):
                raise ValueError("CORS_ORIGINS must contain exact origins")
        return cls(env, issuer, audience, database, namespace, anonymous, origins)
