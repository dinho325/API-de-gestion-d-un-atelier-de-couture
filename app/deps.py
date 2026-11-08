"""Dépendances FastAPI : utilisateur connecté et contrôle des rôles (RG22)."""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import Role
from app.errors import Interdit, NonAuthentifie
from app.models import Utilisateur
from app.security import decoder_jeton

# auto_error=False : c'est nous qui renvoyons le 401 avec un message en français
schema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def utilisateur_courant(
    jeton: str | None = Depends(schema_oauth2), db: Session = Depends(get_db)
) -> Utilisateur:
    if not jeton:
        raise NonAuthentifie("Authentification requise.")
    utilisateur_id = decoder_jeton(jeton)
    if utilisateur_id is None:
        raise NonAuthentifie("Jeton invalide ou expiré.")
    utilisateur = db.get(Utilisateur, utilisateur_id)
    # RG22 : un compte désactivé est refusé immédiatement, même avec un jeton valide
    if utilisateur is None or not utilisateur.actif:
        raise NonAuthentifie("Compte inconnu ou désactivé.")
    return utilisateur


def exiger_roles(*roles: Role):
    """Fabrique une dépendance qui n'accepte que ces rôles (+ l'admin, qui peut tout)."""
    autorises = {Role.admin, *roles}

    def verifier(utilisateur: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
        if utilisateur.role not in autorises:
            noms = " ou ".join(sorted(r.value for r in autorises))
            raise Interdit(f"Droits insuffisants : rôle requis : {noms}.")
        return utilisateur

    return verifier


# Raccourcis lisibles dans les routes
tout_utilisateur = utilisateur_courant
admin_seulement = exiger_roles()
accueil_ou_admin = exiger_roles(Role.accueil)
tailleur_ou_admin = exiger_roles(Role.tailleur)
