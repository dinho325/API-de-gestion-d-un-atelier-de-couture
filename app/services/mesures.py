"""Prises de mesures (RG2, RG3, RG4)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Conflit, DonneeInvalide, NonTrouve
from app.models import CHAMPS_MESURES, Commande, Mesure, Utilisateur
from app.schemas.mesure import MesureCreate, MesureUpdate
from app.services.clients import obtenir_client
from app.utils import aujourdhui


def creer_mesure(db: Session, client_id: int, data: MesureCreate, tailleur: Utilisateur) -> Mesure:
    obtenir_client(db, client_id)
    champs = data.model_dump()
    champs["date_prise"] = champs["date_prise"] or aujourdhui()
    mesure = Mesure(client_id=client_id, prise_par_id=tailleur.id, **champs)
    db.add(mesure)
    db.flush()
    return mesure


def historique_mesures(db: Session, client_id: int) -> list[Mesure]:
    """RG3 : tout l'historique, la plus récente d'abord."""
    obtenir_client(db, client_id)
    return list(db.scalars(
        select(Mesure).where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    ))


def dernieres_mesures(db: Session, client_id: int) -> Mesure | None:
    """RG3 : la prise de date la plus récente (à date égale, la dernière saisie)."""
    return db.scalar(
        select(Mesure).where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc()).limit(1)
    )


def obtenir_dernieres_ou_404(db: Session, client_id: int) -> Mesure:
    obtenir_client(db, client_id)
    mesure = dernieres_mesures(db, client_id)
    if mesure is None:
        raise NonTrouve("Ce client n'a aucune prise de mesures.")
    return mesure


def obtenir_mesure(db: Session, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise NonTrouve("Prise de mesures introuvable.")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, data: MesureUpdate) -> Mesure:
    mesure = obtenir_mesure(db, mesure_id)
    champs = data.model_dump(exclude_unset=True)
    if champs.get("date_prise") is None:
        champs.pop("date_prise", None)  # la date ne peut pas être vidée
    for nom, valeur in champs.items():
        setattr(mesure, nom, valeur)
    # RG2 : la correction ne doit pas supprimer toutes les mesures
    if all(getattr(mesure, c) is None for c in CHAMPS_MESURES):
        db.rollback()
        raise DonneeInvalide("Une prise de mesures doit contenir au moins une mesure.")
    db.flush()
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    mesure = obtenir_mesure(db, mesure_id)
    if db.scalar(select(Commande.id).where(Commande.mesure_id == mesure.id).limit(1)) is not None:
        raise Conflit("Ces mesures sont utilisées par une commande : suppression impossible.")  # RG4
    db.delete(mesure)
    db.flush()
