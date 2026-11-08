from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_seulement, tout_utilisateur
from app.models import Utilisateur
from app.schemas.catalogue import TypeVetementCreate, TypeVetementLecture, TypeVetementUpdate
from app.services import catalogue as service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post("", response_model=TypeVetementLecture, status_code=status.HTTP_201_CREATED)
def creer(data: TypeVetementCreate, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    prestation = service.creer_prestation(db, data)
    db.commit()
    return prestation


@router.get("", response_model=list[TypeVetementLecture])
def lister(
    actifs_seulement: bool = True,
    db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur),
):
    return service.lister_prestations(db, actifs_seulement)


@router.get("/{prestation_id}", response_model=TypeVetementLecture)
def detail(prestation_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_prestation(db, prestation_id)


@router.patch("/{prestation_id}", response_model=TypeVetementLecture)
def modifier(
    prestation_id: int, data: TypeVetementUpdate, db: Session = Depends(get_db),
    _: Utilisateur = Depends(admin_seulement),
):
    prestation = service.modifier_prestation(db, prestation_id, data)
    db.commit()
    return prestation
