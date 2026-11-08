"""Cœur métier : commandes, montants, lignes, workflow des statuts.

Toute la logique (RG5 à RG15) est ici, pas dans les routes. Les fonctions
reçoivent une session SQLAlchemy et font des flush() : c'est le routeur qui
valide la transaction (commit).
"""
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import and_, not_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.enums import Role, StatutCommande
from app.errors import Conflit, DonneeInvalide, Interdit, NonTrouve
from app.models import (
    Client, Commande, HistoriqueStatut, LigneCommande, Mesure, TypeVetement, Utilisateur,
)
from app.schemas.commande import CommandeCreate, CommandeUpdate, LigneCreate
from app.services.clients import obtenir_client
from app.services.mesures import dernieres_mesures
from app.services.pagination import paginer
from app.utils import aujourdhui

S = StatutCommande
STATUTS_FINAUX = (S.livree, S.annulee)

# Workflow (section 6). « terminee → livree » n'est possible que par la
# confirmation de livraison, jamais par la route de changement de statut.
TRANSITIONS: dict[StatutCommande, set[StatutCommande]] = {
    S.en_attente: {S.en_coupe, S.annulee},
    S.en_coupe: {S.en_couture, S.annulee},
    S.en_couture: {S.essayage, S.terminee, S.annulee},
    S.essayage: {S.retouches, S.terminee, S.annulee},
    S.retouches: {S.essayage, S.terminee, S.annulee},
    S.terminee: {S.livree},
    S.livree: set(),
    S.annulee: set(),
}


# ------------------------------------------------------------------ lecture
def obtenir_commande(db: Session, commande_id: int) -> Commande:
    requete = (
        select(Commande).where(Commande.id == commande_id)
        .options(
            joinedload(Commande.client),
            selectinload(Commande.lignes).joinedload(LigneCommande.type_vetement),
            selectinload(Commande.paiements),
            joinedload(Commande.livraison),
        )
    )
    commande = db.scalars(requete).unique().one_or_none()
    if commande is None:
        raise NonTrouve("Commande introuvable.")
    return commande


def condition_en_retard():
    """RG11 sous forme de condition SQL (pour filtrer et compter)."""
    return and_(
        Commande.date_livraison_prevue < aujourdhui(),
        Commande.statut.not_in(STATUTS_FINAUX),
    )


def lister_commandes(
    db: Session, limit: int, offset: int, *, statut: StatutCommande | None = None,
    client_id: int | None = None, en_retard: bool | None = None,
    date_min: date | None = None, date_max: date | None = None, numero: str | None = None,
) -> tuple[list[Commande], int]:
    requete = (
        select(Commande).options(joinedload(Commande.client))
        .order_by(Commande.date_commande.desc(), Commande.id.desc())
    )
    if statut:
        requete = requete.where(Commande.statut == statut)
    if client_id is not None:
        requete = requete.where(Commande.client_id == client_id)
    if en_retard is True:
        requete = requete.where(condition_en_retard())
    elif en_retard is False:
        requete = requete.where(not_(condition_en_retard()))
    if date_min:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.ilike(f"%{numero}%"))
    return paginer(db, requete, limit, offset)


def commandes_du_client(db: Session, client_id: int, limit: int, offset: int):
    obtenir_client(db, client_id)
    return lister_commandes(db, limit, offset, client_id=client_id)


def historique(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    commande = obtenir_commande(db, commande_id)
    return list(db.scalars(
        select(HistoriqueStatut).where(HistoriqueStatut.commande_id == commande.id)
        .order_by(HistoriqueStatut.date_changement, HistoriqueStatut.id)
    ))


# ------------------------------------------------------------------ calculs
def recalculer_montants(commande: Commande) -> None:
    """RG7 : total = Σ(quantité × prix unitaire) − remise ; payé = Σ paiements."""
    commande.montant_total = commande.montant_prestations - commande.remise
    commande.montant_paye = sum(p.montant for p in commande.paiements)


def _verifier_remise(somme_prestations: int, remise: int) -> None:
    if remise > somme_prestations:
        raise DonneeInvalide(
            f"La remise ({remise} FCFA) ne peut pas dépasser la somme des "
            f"prestations ({somme_prestations} FCFA)."
        )


def verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable."""
    if commande.statut in STATUTS_FINAUX:
        raise Conflit(f"La commande est « {commande.statut.value} » : elle n'est plus modifiable.")


def _prestation_commandable(db: Session, type_vetement_id: int) -> TypeVetement:
    prestation = db.get(TypeVetement, type_vetement_id)
    if prestation is None:
        raise NonTrouve(f"Prestation {type_vetement_id} introuvable dans le catalogue.")
    if not prestation.actif:
        raise DonneeInvalide(f"La prestation « {prestation.nom} » n'est plus commandable.")  # RG6
    return prestation


def _construire_ligne(db: Session, data: LigneCreate) -> tuple[LigneCommande, TypeVetement]:
    prestation = _prestation_commandable(db, data.type_vetement_id)
    prix = prestation.prix_base if data.prix_unitaire is None else data.prix_unitaire  # RG6
    ligne = LigneCommande(
        type_vetement=prestation, description=data.description,
        quantite=data.quantite, prix_unitaire=prix,
    )
    return ligne, prestation


def _mesure_du_client(db: Session, client: Client, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise NonTrouve("Prise de mesures introuvable.")
    if mesure.client_id != client.id:
        raise DonneeInvalide("Ces mesures n'appartiennent pas au client de la commande.")  # RG9
    return mesure


def _noter_historique(
    commande: Commande, ancien: StatutCommande | None, nouveau: StatutCommande,
    commentaire: str | None, utilisateur: Utilisateur,
) -> None:
    commande.historique.append(HistoriqueStatut(
        ancien_statut=ancien, nouveau_statut=nouveau,
        commentaire=commentaire, utilisateur_id=utilisateur.id,
    ))  # RG15


# ----------------------------------------------------------------- création
def creer_commande(db: Session, data: CommandeCreate, utilisateur: Utilisateur) -> Commande:
    client = obtenir_client(db, data.client_id)

    lignes, delais = [], []
    for ligne_data in data.lignes:
        ligne, prestation = _construire_ligne(db, ligne_data)
        lignes.append(ligne)
        delais.append(prestation.delai_jours)

    somme = sum(l.quantite * l.prix_unitaire for l in lignes)
    _verifier_remise(somme, data.remise)

    date_commande = aujourdhui()
    if data.date_livraison_prevue is None:
        prevue = date_commande + timedelta(days=max(delais))  # RG8
    elif data.date_livraison_prevue < date_commande:
        raise DonneeInvalide("La date de livraison prévue ne peut pas précéder la date de commande.")
    else:
        prevue = data.date_livraison_prevue

    # RG9 : mesures du client ; sans précision, les dernières mesures s'il en a
    if data.mesure_id is not None:
        mesure_id = _mesure_du_client(db, client, data.mesure_id).id
    else:
        derniere = dernieres_mesures(db, client.id)
        mesure_id = derniere.id if derniere else None

    commande = Commande(
        numero=f"TMP-{uuid4().hex}",  # remplacé juste après, quand l'id est connu
        client=client, mesure_id=mesure_id, statut=S.en_attente,
        date_commande=date_commande, date_livraison_prevue=prevue,
        remise=data.remise, notes=data.notes, cree_par_id=utilisateur.id,
        montant_total=0, montant_paye=0,
    )
    commande.lignes = lignes
    recalculer_montants(commande)
    db.add(commande)
    db.flush()

    commande.numero = f"CMD-{date_commande.year}-{commande.id:05d}"  # RG5
    _noter_historique(commande, None, S.en_attente, "Création de la commande", utilisateur)
    db.flush()
    return commande


# ------------------------------------------------------------- modification
def modifier_commande(db: Session, commande_id: int, data: CommandeUpdate) -> Commande:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # RG12
    champs = data.model_dump(exclude_unset=True)

    if "mesure_id" in champs:
        if champs["mesure_id"] is None:
            commande.mesure_id = None
        else:
            commande.mesure_id = _mesure_du_client(db, commande.client, champs["mesure_id"]).id

    if "date_livraison_prevue" in champs:
        nouvelle = champs["date_livraison_prevue"]
        if nouvelle is None:  # retour à la valeur par défaut (RG8)
            delai = max(l.type_vetement.delai_jours for l in commande.lignes)
            nouvelle = commande.date_commande + timedelta(days=delai)
        elif nouvelle < commande.date_commande:
            raise DonneeInvalide("La date de livraison prévue ne peut pas précéder la date de commande.")
        commande.date_livraison_prevue = nouvelle

    if "remise" in champs:
        _verifier_remise(commande.montant_prestations, champs["remise"])
        commande.remise = champs["remise"]
    if "notes" in champs:
        commande.notes = champs["notes"]

    _appliquer_montants(commande)
    db.flush()
    return commande


def _appliquer_montants(commande: Commande) -> None:
    """Recalcule les montants en refusant de passer sous le montant déjà payé (RG7)."""
    nouveau_total = commande.montant_prestations - commande.remise
    if nouveau_total < commande.montant_paye:
        raise Conflit(
            f"Le nouveau total ({nouveau_total} FCFA) serait inférieur au montant déjà "
            f"payé ({commande.montant_paye} FCFA)."
        )
    recalculer_montants(commande)


def _verifier_lignes_modifiables(commande: Commande) -> None:
    verifier_modifiable(commande)
    if commande.statut != S.en_attente:  # RG10
        raise Conflit(
            "Les lignes ne sont modifiables que tant que la commande est « en_attente » "
            f"(statut actuel : {commande.statut.value})."
        )


def ajouter_ligne(db: Session, commande_id: int, data: LigneCreate) -> Commande:
    commande = obtenir_commande(db, commande_id)
    _verifier_lignes_modifiables(commande)
    ligne, _ = _construire_ligne(db, data)
    commande.lignes.append(ligne)
    recalculer_montants(commande)
    db.flush()
    return commande


def retirer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    commande = obtenir_commande(db, commande_id)
    ligne = next((l for l in commande.lignes if l.id == ligne_id), None)
    if ligne is None:
        raise NonTrouve("Ligne introuvable dans cette commande.")
    _verifier_lignes_modifiables(commande)
    if len(commande.lignes) == 1:
        raise Conflit("Une commande doit garder au moins une ligne.")  # RG10
    restantes = commande.montant_prestations - ligne.sous_total
    if commande.remise > restantes:
        raise Conflit(
            "Impossible de retirer cette ligne : la remise dépasserait la somme des "
            "prestations restantes. Réduisez d'abord la remise."
        )
    commande.lignes.remove(ligne)
    _appliquer_montants(commande)
    db.flush()
    return commande


# ----------------------------------------------------------------- workflow
def _decrire_statuts(statuts: set[StatutCommande]) -> str:
    if not statuts:
        return "aucun"
    noms = sorted(s.value for s in statuts)
    return ", ".join(
        f"{n} (uniquement par la confirmation de livraison)" if n == "livree" else n
        for n in noms
    )


def changer_statut(
    db: Session, commande_id: int, cible: StatutCommande,
    commentaire: str | None, utilisateur: Utilisateur,
) -> Commande:
    commande = obtenir_commande(db, commande_id)

    # RG14 : le tailleur ne peut pas annuler
    if cible == S.annulee and utilisateur.role == Role.tailleur:
        raise Interdit("Un tailleur ne peut pas annuler une commande.")
    # RG13
    if cible == commande.statut:
        raise Conflit(f"La commande est déjà au statut « {cible.value} ».")
    if cible == S.livree:
        raise Conflit(
            "Le statut « livree » ne peut pas être posé directement : "
            "utilisez la confirmation de livraison (POST /commandes/{id}/livraison/confirmer)."
        )
    possibles = TRANSITIONS[commande.statut]
    if cible not in possibles:
        raise Conflit(
            f"Transition interdite : {commande.statut.value} → {cible.value}. "
            f"Statuts possibles : {_decrire_statuts(possibles)}"
        )
    # RG14 : annuler une commande déjà payée en partie exige une explication
    if cible == S.annulee and commande.montant_paye > 0 and not (commentaire or "").strip():
        raise DonneeInvalide(
            f"Cette commande a reçu {commande.montant_paye} FCFA : un commentaire est "
            "obligatoire pour expliquer le sort de l'argent (remboursement, avoir...)."
        )

    ancien = commande.statut
    commande.statut = cible
    _noter_historique(commande, ancien, cible, commentaire, utilisateur)  # RG15
    db.flush()
    return commande
