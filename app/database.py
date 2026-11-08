"""Connexion à PostgreSQL : moteur, fabrique de sessions, classe de base."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False : après commit(), les objets restent lisibles sans
# nouvelle requête, ce qui permet de les renvoyer tels quels dans la réponse.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête, fermée à la fin."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
