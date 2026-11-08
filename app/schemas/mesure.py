from datetime import date

from pydantic import Field, model_validator

from app.models import CHAMPS_MESURES
from app.schemas.common import SchemaEntree, SchemaLecture

# RG2 : chaque mesure est strictement positive et <= 300 cm
Cm = Field(None, gt=0, le=300, description="Mesure en centimètres")


class _Mesures(SchemaEntree):
    taille_cm: float | None = Cm
    tour_cou: float | None = Cm
    carrure_dos: float | None = Cm
    longueur_epaule: float | None = Cm
    tour_poitrine: float | None = Cm
    tour_taille: float | None = Cm
    tour_bassin: float | None = Cm
    longueur_manche: float | None = Cm
    tour_bras: float | None = Cm
    tour_poignet: float | None = Cm
    longueur_dos: float | None = Cm
    longueur_haut: float | None = Cm
    longueur_pantalon: float | None = Cm
    tour_cuisse: float | None = Cm
    tour_genou: float | None = Cm
    bas_pantalon: float | None = Cm
    entrejambe: float | None = Cm
    longueur_robe: float | None = Cm


class MesureCreate(_Mesures):
    date_prise: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _au_moins_une_mesure(self):
        if all(getattr(self, c) is None for c in CHAMPS_MESURES):
            raise ValueError("Une prise de mesures doit contenir au moins une mesure.")
        return self


class MesureUpdate(_Mesures):
    """Correction partielle. Envoyer une mesure à null l'efface.
    Le service vérifie qu'il en reste au moins une (RG2)."""
    date_prise: date | None = None
    notes: str | None = None


class MesureLecture(_Mesures, SchemaLecture):
    id: int
    client_id: int
    date_prise: date
    prise_par_id: int
    notes: str | None
