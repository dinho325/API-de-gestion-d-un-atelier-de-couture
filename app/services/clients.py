"""Règles de gestion des clients (RG1, RG4) et résumé financier."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.enums import Genre, StatutCommande
from app.errors import Conflit, NonTrouve
from app.models import Client, Commande, Mesure
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.pagination import paginer


def _verifier_telephone_libre(db: Session, telephone: str, sauf_client_id: int | None = None):
    requete = select(Client.id).where(Client.telephone == telephone)
    if sauf_client_id is not None:
        requete = requete.where(Client.id != sauf_client_id)  # garder son numéro n'est pas un doublon
    if db.scalar(requete) is not None:
        raise Conflit(f"Un client existe déjà avec le téléphone {telephone}.")


def creer_client(db: Session, data: ClientCreate) -> Client:
    _verifier_telephone_libre(db, data.telephone)
    client = Client(**data.model_dump())
    db.add(client)
    db.flush()
    return client


def obtenir_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise NonTrouve("Client introuvable.")
    return client


def lister_clients(
    db: Session, q: str | None, genre: Genre | None, limit: int, offset: int
) -> tuple[list[Client], int]:
    requete = select(Client).order_by(Client.nom, Client.prenom, Client.id)
    if q:
        motif = f"%{q}%"
        requete = requete.where(or_(
            Client.nom.ilike(motif), Client.prenom.ilike(motif), Client.telephone.ilike(motif),
        ))
    if genre:
        requete = requete.where(Client.genre == genre)
    return paginer(db, requete, limit, offset)


def modifier_client(db: Session, client_id: int, data: ClientUpdate) -> Client:
    client = obtenir_client(db, client_id)
    champs = data.model_dump(exclude_unset=True)  # PATCH : seulement ce qui est envoyé
    if "telephone" in champs:
        _verifier_telephone_libre(db, champs["telephone"], sauf_client_id=client.id)
    for nom, valeur in champs.items():
        setattr(client, nom, valeur)
    db.flush()
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    client = obtenir_client(db, client_id)
    if db.scalar(select(func.count(Commande.id)).where(Commande.client_id == client.id)):
        raise Conflit("Ce client a des commandes : il ne peut pas être supprimé.")  # RG4
    db.delete(client)  # supprime aussi ses mesures (cascade)
    db.flush()


def resume_client(db: Session, client_id: int) -> dict:
    """Commandes annulées exclues."""
    obtenir_client(db, client_id)
    nb, ca, paye, derniere = db.execute(
        select(
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_total), 0),
            func.coalesce(func.sum(Commande.montant_paye), 0),
            func.max(Commande.date_commande),
        ).where(Commande.client_id == client_id, Commande.statut != StatutCommande.annulee)
    ).one()
    a_des_mesures = db.scalar(select(func.count(Mesure.id)).where(Mesure.client_id == client_id)) > 0
    return {
        "nb_commandes": nb, "chiffre_affaires": ca, "total_paye": paye,
        "solde_du": ca - paye, "derniere_commande": derniere, "a_des_mesures": a_des_mesures,
    }
