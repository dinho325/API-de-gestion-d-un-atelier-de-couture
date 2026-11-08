"""Comptes utilisateurs et authentification (RG21 à RG24)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import Role
from app.errors import Conflit, NonAuthentifie, NonTrouve
from app.models import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate
from app.security import hasher_mot_de_passe, verifier_mot_de_passe

# Hash factice : on vérifie toujours un mot de passe, même pour un e-mail
# inconnu, afin que le temps de réponse ne révèle pas si le compte existe.
_HASH_FACTICE = hasher_mot_de_passe("mot-de-passe-factice")
MESSAGE_IDENTIFIANTS = "Identifiants incorrects."


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur:
    utilisateur = db.scalar(select(Utilisateur).where(Utilisateur.email == email.strip().lower()))
    if utilisateur is None:
        verifier_mot_de_passe(mot_de_passe, _HASH_FACTICE)
        raise NonAuthentifie(MESSAGE_IDENTIFIANTS)  # RG23 : même message
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hash):
        raise NonAuthentifie(MESSAGE_IDENTIFIANTS)  # RG23
    if not utilisateur.actif:
        raise NonAuthentifie("Ce compte est désactivé.")
    return utilisateur


def creer_utilisateur(db: Session, data: UtilisateurCreate) -> Utilisateur:
    email = data.email.lower()
    if db.scalar(select(Utilisateur.id).where(Utilisateur.email == email)):
        raise Conflit(f"Un compte existe déjà avec l'e-mail {email}.")
    utilisateur = Utilisateur(
        email=email, nom_complet=data.nom_complet, role=data.role,
        mot_de_passe_hash=hasher_mot_de_passe(data.mot_de_passe), actif=True,
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def lister_utilisateurs(db: Session) -> list[Utilisateur]:
    return list(db.scalars(select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id)))


def obtenir_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise NonTrouve("Utilisateur introuvable.")
    return utilisateur


def modifier_utilisateur(
    db: Session, utilisateur_id: int, data: UtilisateurUpdate, acteur: Utilisateur
) -> Utilisateur:
    utilisateur = obtenir_utilisateur(db, utilisateur_id)
    champs = data.model_dump(exclude_unset=True)

    # RG24 : un admin ne peut ni se désactiver ni se retirer le rôle admin
    if utilisateur.id == acteur.id:
        if champs.get("actif") is False:
            raise Conflit("Vous ne pouvez pas désactiver votre propre compte.")
        if "role" in champs and champs["role"] != Role.admin:
            raise Conflit("Vous ne pouvez pas retirer votre propre rôle d'administrateur.")

    if "nom_complet" in champs and champs["nom_complet"] is not None:
        utilisateur.nom_complet = champs["nom_complet"]
    if champs.get("role") is not None:
        utilisateur.role = champs["role"]
    if champs.get("actif") is not None:
        utilisateur.actif = champs["actif"]
    if champs.get("mot_de_passe") is not None:
        utilisateur.mot_de_passe_hash = hasher_mot_de_passe(champs["mot_de_passe"])
    db.flush()
    return utilisateur
