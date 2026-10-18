#!/usr/bin/env bash
# One-time PostgreSQL setup for AnHydra on the app server itself (Ubuntu 22.04/24.04).
#
#   sudo bash deploy/setup_postgres.sh                  # checkout at /root/tardiscreen
#   sudo bash deploy/setup_postgres.sh /path/to/checkout
#
# What it does, in order:
#   1. Installs PostgreSQL if missing. It listens on localhost only (Ubuntu's default), so
#      the database is never reachable from the internet.
#   2. Creates database `anhydra` and two roles, as deploy/AUTH.md asks:
#        anhydra_migrate  owns the tables, runs migrations, never used by the running app
#        anhydra_app      what the app logs in as: SELECT/INSERT on both tables, UPDATE on
#                         app_users, nothing else (no DELETE, no DDL, not an owner)
#   3. Runs the Alembic migrations as anhydra_migrate.
#   4. Writes DATABASE_URL (anhydra_app, localhost) into the checkout's .env, after backing
#      the old .env up. Passwords are random and printed nowhere.
#
# Safe to re-run: existing roles get fresh passwords, migrations only apply what's missing,
# and data is never dropped. Restart the app afterwards: systemctl restart tardiscreen
#
# Testing hook: PSQL_ADMIN overrides how the script reaches the server as a superuser.
set -euo pipefail

APP_DIR="${1:-/root/tardiscreen}"
DB_NAME="anhydra"
MIGRATE_ROLE="anhydra_migrate"
APP_ROLE="anhydra_app"
ENV_FILE="$APP_DIR/.env"
PYTHON="$APP_DIR/.venv/bin/python"
PSQL_ADMIN="${PSQL_ADMIN:-runuser -u postgres -- psql}"

step() { printf '\n==> %s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root (sudo bash $0)"
[[ -d "$APP_DIR" ]] || die "no checkout at $APP_DIR"
[[ -x "$PYTHON" ]] || die "no virtualenv at $APP_DIR/.venv. Create it and pip install -r requirements.txt first"
"$PYTHON" -c "import alembic, psycopg, sqlalchemy" 2>/dev/null \
  || die "alembic/psycopg/sqlalchemy missing from the venv. Run: $PYTHON -m pip install -r $APP_DIR/requirements.txt"

if ! command -v psql >/dev/null 2>&1; then
  step "Installing PostgreSQL"
  apt-get update -q
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q postgresql
  systemctl enable --now postgresql
fi

admin() { $PSQL_ADMIN -X -q -v ON_ERROR_STOP=1 "$@"; }
admin -d postgres -c "SELECT 1" >/dev/null || die "cannot reach PostgreSQL as the postgres superuser"

# Hex keeps passwords URL-safe, so they can sit in DATABASE_URL without escaping.
MIGRATE_PW="$(openssl rand -hex 24)"
APP_PW="$(openssl rand -hex 24)"

step "Creating roles and database (existing ones are kept; passwords are rotated)"
# Passwords travel as psql variables and are quoted by psql (:'name'), never spliced into SQL.
admin -d postgres -v migrate_pw="$MIGRATE_PW" -v app_pw="$APP_PW" <<SQL
SELECT format('CREATE ROLE %I LOGIN', '$MIGRATE_ROLE')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$MIGRATE_ROLE') \gexec
SELECT format('CREATE ROLE %I LOGIN', '$APP_ROLE')
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$APP_ROLE') \gexec
ALTER ROLE $MIGRATE_ROLE WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'migrate_pw';
ALTER ROLE $APP_ROLE     WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_pw';
SELECT format('CREATE DATABASE %I OWNER %I', '$DB_NAME', '$MIGRATE_ROLE')
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') \gexec
REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;
GRANT CONNECT ON DATABASE $DB_NAME TO $APP_ROLE;
SQL

# PostgreSQL 14 (Ubuntu 22.04) still lets every role create objects in schema public.
admin -d "$DB_NAME" <<SQL
ALTER SCHEMA public OWNER TO $MIGRATE_ROLE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO $APP_ROLE;
SQL

step "Running migrations as $MIGRATE_ROLE"
(cd "$APP_DIR" && DATABASE_URL="postgresql+psycopg://$MIGRATE_ROLE:$MIGRATE_PW@localhost:5432/$DB_NAME" \
   "$PYTHON" -m alembic upgrade head)

step "Granting the app role only what it needs"
admin -d "$DB_NAME" <<SQL
GRANT SELECT, INSERT, UPDATE ON app_users TO $APP_ROLE;
GRANT SELECT, INSERT ON auth_identities TO $APP_ROLE;
SQL

APP_URL="postgresql+psycopg://$APP_ROLE:$APP_PW@localhost:5432/$DB_NAME"

step "Checking the app role can log in and read, and cannot delete"
(cd "$APP_DIR" && DATABASE_URL="$APP_URL" "$PYTHON" - <<'PY'
import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from app.database import database_engine
from app.settings import Settings
engine = database_engine(os.environ["DATABASE_URL"])
with engine.connect() as c:
    c.execute(text("SELECT count(*) FROM app_users")).scalar_one()
try:
    with engine.begin() as c:
        c.execute(text("DELETE FROM auth_identities WHERE false"))
    raise SystemExit("app role can DELETE; privileges are too broad")
except ProgrammingError:
    pass
engine.dispose()
os.environ.update(APP_ENV="production", AUTH_DEV_ANONYMOUS="false", AUTH0_ISSUER="https://x.example/",
                  AUTH0_AUDIENCE="check", AUTH0_CLAIM_NAMESPACE="https://x.example/claims/")
Settings.from_env()   # the production settings check accepts this URL
print("    ok: connects, reads, cannot delete, accepted by production settings")
PY
)

step "Writing DATABASE_URL into $ENV_FILE"
touch "$ENV_FILE"
cp -p "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d-%H%M%S)"
grep -v '^DATABASE_URL=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
printf 'DATABASE_URL=%s\n' "$APP_URL" >> "$ENV_FILE.tmp"
chmod 600 "$ENV_FILE.tmp"
chown root:root "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE.bak."*

cat <<DONE

Done. PostgreSQL is set up for AnHydra.
  database   $DB_NAME on localhost:5432 (not reachable from outside this server)
  app role   $APP_ROLE  (DATABASE_URL written to $ENV_FILE; old file backed up next to it)

Next:
  1. Make sure $ENV_FILE also has APP_ENV=production, AUTH0_ISSUER, AUTH0_AUDIENCE and
     AUTH0_CLAIM_NAMESPACE (see deploy/AUTH.md).
  2. systemctl restart tardiscreen && systemctl status tardiscreen --no-pager
DONE
