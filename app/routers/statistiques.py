from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_seulement
from app.enums import Granularite
from app.models import Utilisateur
from app.schemas.commande import CommandeResume
from app.schemas.common import Page, Pagination, pagination
from app.schemas.statistiques import (
    ChiffreAffaires, StatTypeVetement, TableauDeBord, TopClient,
)
from app.services import statistiques as service

router = APIRouter(prefix="/statistiques", tags=["Statistiques (admin)"])


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    return service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=ChiffreAffaires)
def chiffre_affaires(
    granularite: Granularite = Granularite.jour,
    date_debut: date | None = None, date_fin: date | None = None,
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement),
):
    return service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[StatTypeVetement])
def types_vetement(
    date_debut: date | None = None, date_fin: date | None = None,
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement),
):
    return service.par_type_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient])
def top_clients(
    date_debut: date | None = None, date_fin: date | None = None,
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement),
):
    return service.top_clients(db, date_debut, date_fin, limite)


@router.get("/impayes", response_model=Page[CommandeResume])
def impayes(
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement),
):
    items, total = service.impayes(db, page.limit, page.offset)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)
