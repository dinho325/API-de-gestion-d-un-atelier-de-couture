from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_seulement
from app.models import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurLecture, UtilisateurUpdate
from app.services import utilisateurs as service

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.post("", response_model=UtilisateurLecture, status_code=status.HTTP_201_CREATED)
def creer(data: UtilisateurCreate, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    utilisateur = service.creer_utilisateur(db, data)
    db.commit()
    return utilisateur


@router.get("", response_model=list[UtilisateurLecture])
def lister(db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    return service.lister_utilisateurs(db)


@router.get("/{utilisateur_id}", response_model=UtilisateurLecture)
def detail(utilisateur_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    return service.obtenir_utilisateur(db, utilisateur_id)


@router.patch("/{utilisateur_id}", response_model=UtilisateurLecture)
def modifier(
    utilisateur_id: int, data: UtilisateurUpdate, db: Session = Depends(get_db),
    admin: Utilisateur = Depends(admin_seulement),
):
    utilisateur = service.modifier_utilisateur(db, utilisateur_id, data, admin)
    db.commit()
    return utilisateur
