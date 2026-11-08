"""Livraisons (RG18, RG19, RG20)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.enums import ModeLivraison, StatutCommande, StatutLivraison
from app.errors import Conflit, DonneeInvalide, NonTrouve
from app.models import Commande, Livraison, Utilisateur
from app.schemas.commande import ConfirmationLivraison, LivraisonPlanification
from app.services.commandes import (
    _noter_historique, obtenir_commande, verifier_modifiable,
)
from app.utils import aujourdhui


def planifier_livraison(db: Session, commande_id: int, data: LivraisonPlanification) -> Livraison:
    """Crée la livraison ou, si elle existe, la modifie (jamais deux)."""
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # 409 si livrée ou annulée
    if data.date_prevue < commande.date_commande:
        raise DonneeInvalide("La date de livraison ne peut pas précéder la date de commande.")

    livraison = commande.livraison
    if livraison is None:
        livraison = Livraison(statut=StatutLivraison.planifiee)
        commande.livraison = livraison
    livraison.mode = data.mode
    livraison.date_prevue = data.date_prevue
    livraison.adresse = data.adresse
    livraison.livreur = data.livreur
    livraison.notes = data.notes
    commande.date_livraison_prevue = data.date_prevue  # RG18
    db.flush()
    return livraison


def obtenir_livraison(db: Session, commande_id: int) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    if commande.livraison is None:
        raise NonTrouve("Aucune livraison n'est planifiée pour cette commande.")
    return commande.livraison


def confirmer_livraison(
    db: Session, commande_id: int, data: ConfirmationLivraison, utilisateur: Utilisateur
) -> Commande:
    commande = obtenir_commande(db, commande_id)

    if commande.statut != StatutCommande.terminee:  # RG19
        raise Conflit(
            "La livraison ne peut être confirmée que pour une commande « terminee » "
            f"(statut actuel : {commande.statut.value})."
        )
    date_effective = data.date_effective or aujourdhui()
    if date_effective > aujourdhui():
        raise DonneeInvalide("La date effective de livraison ne peut pas être dans le futur.")
    if date_effective < commande.date_commande:
        raise DonneeInvalide("La date effective ne peut pas précéder la date de commande.")

    solde = commande.solde
    if solde > 0 and not data.autoriser_solde_impaye:  # RG19
        raise Conflit(
            f"Livraison refusée : il reste {solde} FCFA impayés. Encaissez le solde ou "
            "envoyez autoriser_solde_impaye = true."
        )

    commentaire = "Livraison confirmée"
    if solde > 0:
        commentaire += f" avec solde impayé autorisé ({solde} FCFA restant dus)"

    # RG20
    if commande.livraison is None:
        commande.livraison = Livraison(
            mode=ModeLivraison.retrait_atelier, date_prevue=commande.date_livraison_prevue,
        )
    commande.livraison.date_effective = date_effective
    commande.livraison.statut = StatutLivraison.livree
    commande.date_livraison_reelle = date_effective
    commande.statut = StatutCommande.livree
    _noter_historique(commande, StatutCommande.terminee, StatutCommande.livree, commentaire, utilisateur)
    db.flush()
    return commande


def lister_livraisons(
    db: Session, statut: StatutLivraison | None, date_min: date | None, date_max: date | None
) -> list[Livraison]:
    requete = (
        select(Livraison)
        .options(joinedload(Livraison.commande).joinedload(Commande.client))
        .order_by(Livraison.date_prevue, Livraison.id)
    )
    if statut:
        requete = requete.where(Livraison.statut == statut)
    if date_min:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max:
        requete = requete.where(Livraison.date_prevue <= date_max)
    return list(db.scalars(requete).unique())
