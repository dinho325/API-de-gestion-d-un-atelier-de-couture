"""Statistiques réservées à l'administrateur.

Définitions (section 6) :
- chiffre d'affaires : total des commandes NON annulées, daté à la date de commande ;
- encaissé : total des paiements, daté à la date de paiement ;
- reste à encaisser : somme des soldes des commandes non annulées.
"""
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import Granularite, StatutCommande, StatutLivraison
from app.errors import DonneeInvalide
from app.models import Client, Commande, LigneCommande, Livraison, Paiement, TypeVetement
from app.services.commandes import condition_en_retard
from app.utils import aujourdhui

NON_ANNULEE = Commande.statut != StatutCommande.annulee


def resoudre_periode(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    """Par défaut : du 1er du mois à aujourd'hui."""
    fin = date_fin or aujourdhui()
    debut = date_debut or aujourdhui().replace(day=1)
    if debut > fin:
        raise DonneeInvalide("date_debut doit être antérieure ou égale à date_fin.")
    return debut, fin


def _somme(db: Session, colonne, *conditions) -> int:
    return db.scalar(select(func.coalesce(func.sum(colonne), 0)).where(*conditions)) or 0


def tableau_de_bord(db: Session) -> dict:
    aujourd = aujourdhui()
    debut_mois = aujourd.replace(day=1)
    mois_suivant = date(debut_mois.year + (debut_mois.month // 12), debut_mois.month % 12 + 1, 1)
    dans_le_mois = (Commande.date_commande >= debut_mois, Commande.date_commande < mois_suivant)

    par_statut = {s.value: 0 for s in StatutCommande}  # tous les statuts, même à 0
    for statut, nombre in db.execute(select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)):
        par_statut[statut.value] = nombre

    return {
        "mois": debut_mois.strftime("%Y-%m"),
        "chiffre_affaires_mois": _somme(db, Commande.montant_total, NON_ANNULEE, *dans_le_mois),
        "encaisse_mois": _somme(
            db, Paiement.montant,
            Paiement.date_paiement >= debut_mois, Paiement.date_paiement < mois_suivant,
        ),
        "nb_commandes_mois": db.scalar(
            select(func.count(Commande.id)).where(NON_ANNULEE, *dans_le_mois)
        ),
        "reste_a_encaisser": _somme(db, Commande.montant_total - Commande.montant_paye, NON_ANNULEE),
        "commandes_par_statut": par_statut,
        "nb_commandes_en_retard": db.scalar(
            select(func.count(Commande.id)).where(condition_en_retard())
        ),
        "commandes_pretes_a_livrer": par_statut[StatutCommande.terminee.value],
        "livraisons_du_jour": db.scalar(
            select(func.count(Livraison.id)).where(
                Livraison.date_prevue == aujourd, Livraison.statut == StatutLivraison.planifiee
            )
        ),
    }


def chiffre_affaires(
    db: Session, granularite: Granularite, date_debut: date | None, date_fin: date | None
) -> dict:
    debut, fin = resoudre_periode(date_debut, date_fin)
    format_periode = "%Y-%m-%d" if granularite == Granularite.jour else "%Y-%m"

    ca: dict[str, int] = defaultdict(int)
    encaisse: dict[str, int] = defaultdict(int)
    for jour, total in db.execute(
        select(Commande.date_commande, Commande.montant_total)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
    ):
        ca[jour.strftime(format_periode)] += total
    for jour, montant in db.execute(
        select(Paiement.date_paiement, Paiement.montant)
        .where(Paiement.date_paiement.between(debut, fin))
    ):
        encaisse[jour.strftime(format_periode)] += montant

    periodes = [  # seules les périodes avec activité
        {"periode": p, "chiffre_affaires": ca.get(p, 0), "encaisse": encaisse.get(p, 0)}
        for p in sorted(set(ca) | set(encaisse))
    ]
    return {
        "granularite": granularite, "date_debut": debut, "date_fin": fin,
        "total_chiffre_affaires": sum(ca.values()), "total_encaisse": sum(encaisse.values()),
        "periodes": periodes,
    }


def par_type_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict]:
    debut, fin = resoudre_periode(date_debut, date_fin)
    ca = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire)  # avant remise
    lignes = db.execute(
        select(TypeVetement.id, TypeVetement.nom, func.sum(LigneCommande.quantite), ca)
        .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(ca.desc(), TypeVetement.nom)
    )
    return [
        {"type_vetement_id": i, "nom": nom, "quantite": q, "chiffre_affaires": c}
        for i, nom, q, c in lignes
    ]


def top_clients(db: Session, date_debut: date | None, date_fin: date | None, limite: int) -> list[dict]:
    debut, fin = resoudre_periode(date_debut, date_fin)
    ca = func.sum(Commande.montant_total)
    lignes = db.execute(
        select(
            Client.id, Client.prenom, Client.nom, Client.telephone,
            func.count(Commande.id), ca, func.sum(Commande.montant_total - Commande.montant_paye),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(Client.id, Client.prenom, Client.nom, Client.telephone)
        .order_by(ca.desc(), Client.nom)
        .limit(limite)
    )
    return [
        {"client_id": i, "client_nom": f"{prenom} {nom}", "telephone": tel,
         "nb_commandes": nb, "chiffre_affaires": c, "solde_du": solde}
        for i, prenom, nom, tel, nb, c, solde in lignes
    ]


def impayes(db: Session, limit: int, offset: int):
    """Commandes non annulées non soldées, les plus urgentes d'abord."""
    from sqlalchemy.orm import joinedload
    from app.services.pagination import paginer

    requete = (
        select(Commande).options(joinedload(Commande.client))
        .where(NON_ANNULEE, Commande.montant_total > Commande.montant_paye)
        .order_by(Commande.date_livraison_prevue, Commande.id)
    )
    return paginer(db, requete, limit, offset)
