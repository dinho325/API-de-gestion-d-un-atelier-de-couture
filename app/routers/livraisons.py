from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import accueil_ou_admin, tout_utilisateur
from app.enums import StatutLivraison
from app.models import Utilisateur
from app.schemas.commande import (
    CommandeDetail, ConfirmationLivraison, LivraisonLecture, LivraisonPlanification,
    LivraisonTournee,
)
from app.services import livraisons as service

router = APIRouter(tags=["Livraisons"])


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonLecture)
def planifier(
    commande_id: int, data: LivraisonPlanification, db: Session = Depends(get_db),
    _: Utilisateur = Depends(accueil_ou_admin),
):
    livraison = service.planifier_livraison(db, commande_id, data)
    db.commit()
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonLecture)
def detail(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_livraison(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=CommandeDetail)
def confirmer(
    commande_id: int, data: ConfirmationLivraison | None = None, db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(accueil_ou_admin),
):
    commande = service.confirmer_livraison(db, commande_id, data or ConfirmationLivraison(), utilisateur)
    db.commit()
    return commande


@router.get("/livraisons", response_model=list[LivraisonTournee])
def tournee(
    statut: StatutLivraison | None = None, date_min: date | None = None, date_max: date | None = None,
    db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur),
):
    return service.lister_livraisons(db, statut, date_min, date_max)
