from pydantic import Field

from app.schemas.common import SchemaEntree, SchemaLecture


class TypeVetementCreate(SchemaEntree):
    nom: str = Field(min_length=1, max_length=100)
    description: str | None = None
    prix_base: int = Field(ge=0)
    delai_jours: int = Field(ge=0, le=365)


class TypeVetementUpdate(SchemaEntree):
    nom: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    prix_base: int | None = Field(None, ge=0)
    delai_jours: int | None = Field(None, ge=0, le=365)
    actif: bool | None = None


class TypeVetementLecture(SchemaLecture):
    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
