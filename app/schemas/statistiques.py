from datetime import date

from app.enums import Granularite
from app.schemas.common import SchemaLecture


class TableauDeBord(SchemaLecture):
    mois: str
    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int
    reste_a_encaisser: int
    commandes_par_statut: dict[str, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class PointChiffreAffaires(SchemaLecture):
    periode: str  # « 2026-03-15 » (jour) ou « 2026-03 » (mois)
    chiffre_affaires: int
    encaisse: int


class ChiffreAffaires(SchemaLecture):
    granularite: Granularite
    date_debut: date
    date_fin: date
    total_chiffre_affaires: int
    total_encaisse: int
    periodes: list[PointChiffreAffaires]


class StatTypeVetement(SchemaLecture):
    type_vetement_id: int
    nom: str
    quantite: int
    chiffre_affaires: int


class TopClient(SchemaLecture):
    client_id: int
    client_nom: str
    telephone: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int
