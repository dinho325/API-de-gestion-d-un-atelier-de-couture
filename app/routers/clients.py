from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_seulement, tout_utilisateur
from app.enums import Genre
from app.models import Utilisateur
from app.schemas.client import ClientCreate, ClientLecture, ClientResume, ClientUpdate
from app.schemas.commande import CommandeResume
from app.schemas.common import Page, Pagination, pagination
from app.services import clients as service
from app.services import commandes as service_commandes

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientLecture, status_code=status.HTTP_201_CREATED)
def creer(data: ClientCreate, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    client = service.creer_client(db, data)
    db.commit()
    return client


@router.get("", response_model=Page[ClientLecture])
def lister(
    q: str | None = Query(None, min_length=2, description="Recherche : nom, prénom ou téléphone"),
    genre: Genre | None = None,
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur),
):
    items, total = service.lister_clients(db, q, genre, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{client_id}", response_model=ClientLecture)
def detail(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientLecture)
def modifier(
    client_id: int, data: ClientUpdate, db: Session = Depends(get_db),
    _: Utilisateur = Depends(tout_utilisateur),
):
    client = service.modifier_client(db, client_id, data)
    db.commit()
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    service.supprimer_client(db, client_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/commandes", response_model=Page[CommandeResume])
def commandes_du_client(
    client_id: int, page: Pagination = Depends(pagination),
    db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur),
):
    items, total = service_commandes.commandes_du_client(db, client_id, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{client_id}/resume", response_model=ClientResume)
def resume(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.resume_client(db, client_id)
