from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import tailleur_ou_admin, tout_utilisateur
from app.models import Utilisateur
from app.schemas.mesure import MesureCreate, MesureLecture, MesureUpdate
from app.services import mesures as service

router = APIRouter(tags=["Mesures"])


@router.post("/clients/{client_id}/mesures", response_model=MesureLecture, status_code=status.HTTP_201_CREATED)
def creer(
    client_id: int, data: MesureCreate, db: Session = Depends(get_db),
    tailleur: Utilisateur = Depends(tailleur_ou_admin),
):
    mesure = service.creer_mesure(db, client_id, data, tailleur)
    db.commit()
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureLecture])
def historique(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.historique_mesures(db, client_id)


# Cette route doit rester AVANT /mesures/{id} pour ne pas être confondue avec lui
@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureLecture)
def derniere(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_dernieres_ou_404(db, client_id)


@router.get("/mesures/{mesure_id}", response_model=MesureLecture)
def detail(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tout_utilisateur)):
    return service.obtenir_mesure(db, mesure_id)


@router.patch("/mesures/{mesure_id}", response_model=MesureLecture)
def modifier(
    mesure_id: int, data: MesureUpdate, db: Session = Depends(get_db),
    _: Utilisateur = Depends(tailleur_ou_admin),
):
    mesure = service.modifier_mesure(db, mesure_id, data)
    db.commit()
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tailleur_ou_admin)):
    service.supprimer_mesure(db, mesure_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
