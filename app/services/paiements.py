"""Paiements (RG16, RG17)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import StatutCommande
from app.errors import Conflit, DonneeInvalide, NonTrouve
from app.models import Paiement, Utilisateur
from app.schemas.commande import PaiementCreate
from app.services.commandes import obtenir_commande, recalculer_montants
from app.utils import aujourdhui


def enregistrer_paiement(
    db: Session, commande_id: int, data: PaiementCreate, utilisateur: Utilisateur
) -> Paiement:
    commande = obtenir_commande(db, commande_id)
    date_paiement = data.date_paiement or aujourdhui()
    if date_paiement > aujourdhui():
        raise DonneeInvalide("La date du paiement ne peut pas être dans le futur.")  # RG16
    if commande.statut == StatutCommande.annulee:
        raise Conflit("Cette commande est annulée : aucun paiement n'est possible.")  # RG16
    if data.montant > commande.solde:
        raise Conflit(
            f"Le paiement ({data.montant} FCFA) dépasse le solde restant ({commande.solde} FCFA)."
        )  # RG16

    paiement = Paiement(
        montant=data.montant, mode=data.mode, reference=data.reference,
        date_paiement=date_paiement, enregistre_par_id=utilisateur.id,
    )
    commande.paiements.append(paiement)
    recalculer_montants(commande)
    db.flush()
    return paiement


def lister_paiements(db: Session, commande_id: int) -> list[Paiement]:
    commande = obtenir_commande(db, commande_id)
    return list(db.scalars(
        select(Paiement).where(Paiement.commande_id == commande.id).order_by(Paiement.id)
    ))


def annuler_paiement(db: Session, paiement_id: int) -> None:
    """RG17 : supprime le paiement puis recalcule payé et solde."""
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise NonTrouve("Paiement introuvable.")
    commande = obtenir_commande(db, paiement.commande_id)
    commande.paiements.remove(next(p for p in commande.paiements if p.id == paiement_id))
    recalculer_montants(commande)
    db.flush()
