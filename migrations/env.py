"""Migration credentials come only from the operator's environment."""
import os
from alembic import context
from app.database import database_engine


engine = database_engine(os.environ["DATABASE_URL"])
try:
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
