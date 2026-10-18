"""PostgreSQL account storage. No credentials or token/profile payloads are stored."""
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class AccountStoreUnavailable(HTTPException):
    """The database could not answer. Distinct from refusals (e.g. a disabled account) so that
    /score can tell "we couldn't check" apart from "the answer was no"."""
    def __init__(self):
        super().__init__(503, "Account service is temporarily unavailable.")


def database_engine(url):
    parsed = make_url(url).set(drivername="postgresql+psycopg")
    options = parsed.query.get("options", "") + " -c statement_timeout=5000 -c lock_timeout=5000 -c timezone=UTC"
    return create_engine(parsed,
                         pool_pre_ping=True, pool_size=5, max_overflow=5, pool_timeout=5,
                         hide_parameters=True, connect_args={"connect_timeout": 5,
                         "options": options})


LOOKUP = text("""SELECT u.* FROM app_users u JOIN auth_identities i ON i.user_id=u.id
                 WHERE i.issuer=:issuer AND i.subject=:subject""")


class UserStore:
    def __init__(self, engine):
        self.engine = engine

    def resolve(self, issuer, subject):
        identity = dict(issuer=issuer, subject=subject)
        try:
            with self.engine.begin() as connection:
                row = connection.execute(LOOKUP, identity).mappings().first()
                if row is None:
                    try:
                        # Roll back both candidate rows on a concurrent identity conflict.
                        with connection.begin_nested():
                            user_id = uuid4()
                            connection.execute(text("INSERT INTO app_users (id) VALUES (:id)"), {"id": user_id})
                            connection.execute(text("""INSERT INTO auth_identities (issuer, subject, user_id)
                                                       VALUES (:issuer, :subject, :user_id)"""),
                                               {**identity, "user_id": user_id})
                    except IntegrityError as exc:
                        if getattr(exc.orig, "sqlstate", None) != "23505":
                            raise
                    # READ COMMITTED sees the winning transaction after its unique-key wait.
                    row = connection.execute(LOOKUP, identity).mappings().first()
                    if row is None:
                        raise AccountStoreUnavailable()
                if row["status"] != "active":
                    raise HTTPException(403, "This account is disabled.")
                connection.execute(text("""UPDATE app_users SET last_seen_at=now()
                    WHERE id=:id AND (last_seen_at IS NULL OR last_seen_at < now() - interval '15 minutes')"""),
                                   {"id": row["id"]})
                return {key: row[key] for key in ("id", "display_name", "email", "email_verified", "created_at")}
        except SQLAlchemyError:
            raise AccountStoreUnavailable() from None
