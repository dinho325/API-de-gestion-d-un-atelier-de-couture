from datetime import date, datetime

from pydantic import EmailStr, Field, field_validator, model_validator

from app.enums import Genre
from app.schemas.common import SchemaEntree, SchemaLecture
from app.utils import normaliser_telephone


class _ValidationTelephone(SchemaEntree):
    @field_validator("telephone", check_fields=False)
    @classmethod
    def _normaliser(cls, valeur):
        # RG1 : normalisation + validation (ValueError => 422)
        return normaliser_telephone(valeur) if valeur is not None else valeur


class ClientCreate(_ValidationTelephone):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str = Field(min_length=1)
    email: EmailStr | None = None
    adresse: str | None = Field(None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None


class ClientUpdate(_ValidationTelephone):
    """Modification partielle : seuls les champs envoyés sont modifiés."""
    nom: str | None = Field(None, min_length=1, max_length=100)
    prenom: str | None = Field(None, min_length=1, max_length=100)
    telephone: str | None = Field(None, min_length=1)
    email: EmailStr | None = None
    adresse: str | None = Field(None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _champs_obligatoires_non_vides(self):
        # nom, prenom, telephone ne peuvent pas être vidés (null explicite)
        for champ in ("nom", "prenom", "telephone"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ « {champ} » ne peut pas être vidé.")
        return self


class ClientLecture(SchemaLecture):
    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: Genre | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientResume(SchemaLecture):
    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: date | None
    a_des_mesures: bool
