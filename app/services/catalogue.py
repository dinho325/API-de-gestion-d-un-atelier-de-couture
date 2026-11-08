"""Catalogue des prestations."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Conflit, NonTrouve
from app.models import TypeVetement
from app.schemas.catalogue import TypeVetementCreate, TypeVetementUpdate


def _verifier_nom_libre(db: Session, nom: str, sauf_id: int | None = None):
    requete = select(TypeVetement.id).where(TypeVetement.nom == nom)
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    if db.scalar(requete) is not None:
        raise Conflit(f"Une prestation nommée « {nom} » existe déjà.")


def creer_prestation(db: Session, data: TypeVetementCreate) -> TypeVetement:
    _verifier_nom_libre(db, data.nom)
    prestation = TypeVetement(**data.model_dump(), actif=True)
    db.add(prestation)
    db.flush()
    return prestation


def lister_prestations(db: Session, actifs_seulement: bool) -> list[TypeVetement]:
    requete = select(TypeVetement).order_by(TypeVetement.nom)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return list(db.scalars(requete))


def obtenir_prestation(db: Session, prestation_id: int) -> TypeVetement:
    prestation = db.get(TypeVetement, prestation_id)
    if prestation is None:
        raise NonTrouve("Prestation introuvable.")
    return prestation


def modifier_prestation(db: Session, prestation_id: int, data: TypeVetementUpdate) -> TypeVetement:
    prestation = obtenir_prestation(db, prestation_id)
    champs = data.model_dump(exclude_unset=True)
    if "nom" in champs and champs["nom"] is not None:
        _verifier_nom_libre(db, champs["nom"], sauf_id=prestation.id)
    for nom, valeur in champs.items():
        if valeur is not None:  # aucun de ces champs n'est nullable
            setattr(prestation, nom, valeur)
    db.flush()
    return prestation
