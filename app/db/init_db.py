from app.db.base import Base
from app.db.session import engine

# Import models so they register with Base.metadata before create_all.
import app.models  # noqa: F401


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
