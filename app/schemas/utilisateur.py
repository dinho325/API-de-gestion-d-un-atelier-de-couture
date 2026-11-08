from datetime import datetime

from pydantic import EmailStr, Field

from app.enums import Role
from app.schemas.common import SchemaEntree, SchemaLecture


class UtilisateurCreate(SchemaEntree):
    email: EmailStr
    nom_complet: str = Field(min_length=1, max_length=150)
    mot_de_passe: str = Field(min_length=8, max_length=128)  # RG21
    role: Role


class UtilisateurUpdate(SchemaEntree):
    nom_complet: str | None = Field(None, min_length=1, max_length=150)
    role: Role | None = None
    actif: bool | None = None
    mot_de_passe: str | None = Field(None, min_length=8, max_length=128)


class UtilisateurLecture(SchemaLecture):
    """Aucun champ sensible : surtout pas mot_de_passe_hash (RG21)."""
    id: int
    email: str
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime


class Jeton(SchemaEntree):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
