"""Hachage des mots de passe (Argon2) et jetons JWT."""
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings
from app.utils import maintenant

_hasher = PasswordHasher()


def hasher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    try:
        return _hasher.verify(hash_stocke, mot_de_passe)
    except (VerificationError, InvalidHashError):
        return False


def creer_jeton(utilisateur_id: int) -> tuple[str, int]:
    """Retourne (jeton, durée de validité en secondes)."""
    duree = timedelta(minutes=settings.access_token_expire_minutes)
    maintenant_ = maintenant()
    charge = {"sub": str(utilisateur_id), "iat": maintenant_, "exp": maintenant_ + duree}
    jeton = jwt.encode(charge, settings.secret_key, algorithm=settings.algorithm)
    return jeton, int(duree.total_seconds())


def decoder_jeton(jeton: str) -> int | None:
    """Retourne l'id de l'utilisateur, ou None si le jeton est invalide/expiré."""
    try:
        charge = jwt.decode(
            jeton, settings.secret_key, algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
        return int(charge["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
