from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from app.enums import (
    ModeLivraison, ModePaiement, StatutCommande, StatutLivraison,
)
from app.schemas.common import SchemaEntree, SchemaLecture


# ---------- Entrées ----------
class LigneCreate(SchemaEntree):
    type_vetement_id: int
    description: str | None = Field(None, max_length=255)
    quantite: int = Field(1, ge=1, le=1000)
    # RG6 : facultatif, sinon prix_base du catalogue
    prix_unitaire: int | None = Field(None, ge=0)


class CommandeCreate(SchemaEntree):
    client_id: int
    mesure_id: int | None = None
    lignes: list[LigneCreate] = Field(min_length=1)
    remise: int = Field(0, ge=0)
    date_livraison_prevue: date | None = None
    notes: str | None = None


class CommandeUpdate(SchemaEntree):
    mesure_id: int | None = None
    date_livraison_prevue: date | None = None
    remise: int | None = Field(None, ge=0)
    notes: str | None = None

    @model_validator(mode="after")
    def _remise_non_nulle(self):
        if "remise" in self.model_fields_set and self.remise is None:
            raise ValueError("La remise ne peut pas être vide (envoyez 0 pour l'annuler).")
        return self


class ChangementStatut(SchemaEntree):
    statut: StatutCommande
    commentaire: str | None = Field(None, max_length=1000)


class PaiementCreate(SchemaEntree):
    montant: int = Field(gt=0)
    mode: ModePaiement
    reference: str | None = Field(None, max_length=100)
    date_paiement: date | None = None


class LivraisonPlanification(SchemaEntree):
    mode: ModeLivraison
    date_prevue: date
    adresse: str | None = Field(None, max_length=255)
    livreur: str | None = Field(None, max_length=100)
    notes: str | None = None

    @model_validator(mode="after")
    def _adresse_si_domicile(self):
        # RG18
        if self.mode == ModeLivraison.domicile and not self.adresse:
            raise ValueError("Une livraison à domicile exige une adresse.")
        return self


class ConfirmationLivraison(SchemaEntree):
    date_effective: date | None = None
    autoriser_solde_impaye: bool = False


# ---------- Sorties ----------
class LigneLecture(SchemaLecture):
    id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


class PaiementLecture(SchemaLecture):
    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int
    created_at: datetime


class LivraisonLecture(SchemaLecture):
    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None


class LivraisonTournee(LivraisonLecture):
    numero_commande: str
    client_nom: str
    client_telephone: str
    solde_commande: int


class HistoriqueLecture(SchemaLecture):
    id: int
    commande_id: int
    ancien_statut: StatutCommande | None
    nouveau_statut: StatutCommande
    commentaire: str | None
    utilisateur_id: int
    date_changement: datetime


class CommandeResume(SchemaLecture):
    """Élément des listes de commandes."""
    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool


class CommandeDetail(CommandeResume):
    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    montant_prestations: int
    notes: str | None
    cree_par_id: int
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneLecture]
    paiements: list[PaiementLecture]
    livraison: LivraisonLecture | None
