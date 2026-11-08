from sqlalchemy import func, select
from sqlalchemy.orm import Session


def paginer(db: Session, requete, limit: int, offset: int) -> tuple[list, int]:
    """Exécute une requête SELECT avec LIMIT/OFFSET et renvoie (éléments, total)."""
    total = db.scalar(select(func.count()).select_from(requete.order_by(None).subquery()))
    elements = db.scalars(requete.limit(limit).offset(offset)).unique().all()
    return list(elements), total or 0
