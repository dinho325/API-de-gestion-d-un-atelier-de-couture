from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import accueil_ou_admin, tout_utilisateur
from app.enums import StatutCommande
from app.models import Utilisateur
from app.schemas.commande import (
    ChangementStatut, CommandeCreate, CommandeDetail, CommandeResume, CommandeUpdate,
    HistoriqueLecture, LigneCreate,
)
from app.schemas.common import Page, Pagination, pagination
from app.services import commandes as service

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def creer(
    data: CommandeCreate, db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(accueil_ou_admin),
):
    commande = service.creer_commande(db, data, utilisateur)
    db.commit()
    return commande


@router.get("", response_model=Page[CommandeResume])
def lister(
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = Query(None, description="Date de commande minimale"),
    date_max: date | None = Query(None, description="Date de commande maximale"),
    numero: str | None = None,
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur),
):
    items, total = service.lister_commandes(
        db, page.limit, page.offset, statut=statut, client_id=client_id,
        en_retard=en_retard, date_min=date_min, date_max=date_max, numero=numero,
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{commande_id}", response_model=CommandeDetail)
def detail(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_commande(db, commande_id)


@router.patch("/{commande_id}", response_model=CommandeDetail)
def modifier(
    commande_id: int, data: CommandeUpdate, db: Session = Depends(get_db),
    _: Utilisateur = Depends(accueil_ou_admin),
):
    commande = service.modifier_commande(db, commande_id, data)
    db.commit()
    return commande


@router.post("/{commande_id}/statut", response_model=CommandeDetail)
def changer_statut(
    commande_id: int, data: ChangementStatut, db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(tout_utilisateur),
):
    # Tous les rôles peuvent appeler cette route ; les règles RG13/RG14
    # (dont l'interdiction d'annuler pour le tailleur) sont dans le service.
    commande = service.changer_statut(db, commande_id, data.statut, data.commentaire, utilisateur)
    db.commit()
    return commande


@router.get("/{commande_id}/historique", response_model=list[HistoriqueLecture])
def historique(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.historique(db, commande_id)


@router.post("/{commande_id}/lignes", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def ajouter_ligne(
    commande_id: int, data: LigneCreate, db: Session = Depends(get_db),
    _: Utilisateur = Depends(accueil_ou_admin),
):
    commande = service.ajouter_ligne(db, commande_id, data)
    db.commit()
    return commande


@router.delete("/{commande_id}/lignes/{ligne_id}", response_model=CommandeDetail)
def retirer_ligne(
    commande_id: int, ligne_id: int, db: Session = Depends(get_db),
    _: Utilisateur = Depends(accueil_ou_admin),
):
    commande = service.retirer_ligne(db, commande_id, ligne_id)
    db.commit()
    return commande
