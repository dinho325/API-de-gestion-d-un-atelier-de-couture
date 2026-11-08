from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import accueil_ou_admin, admin_seulement, tout_utilisateur
from app.models import Utilisateur
from app.schemas.commande import PaiementCreate, PaiementLecture
from app.services import paiements as service

router = APIRouter(tags=["Paiements"])


@router.post("/commandes/{commande_id}/paiements", response_model=PaiementLecture, status_code=status.HTTP_201_CREATED)
def encaisser(
    commande_id: int, data: PaiementCreate, db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(accueil_ou_admin),
):
    paiement = service.enregistrer_paiement(db, commande_id, data, utilisateur)
    db.commit()
    return paiement


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementLecture])
def lister(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.lister_paiements(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT)
def annuler(paiement_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_seulement)):
    service.annuler_paiement(db, paiement_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
