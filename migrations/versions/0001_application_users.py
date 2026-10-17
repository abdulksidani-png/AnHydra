"""Application users and exact external identity mapping."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE app_users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
        display_name TEXT,
        email TEXT,
        email_verified BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at TIMESTAMPTZ
    )""")
    op.execute("""CREATE TABLE auth_identities (
        issuer TEXT COLLATE "C" NOT NULL,
        subject TEXT COLLATE "C" NOT NULL,
        user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (issuer, subject)
    )""")
    op.execute("CREATE INDEX auth_identities_user_id_idx ON auth_identities(user_id)")


def downgrade():
    op.drop_table("auth_identities")
    op.drop_table("app_users")
