"""Modèles SQLAlchemy 2 (style moderne : Mapped / mapped_column).

Ces classes décrivent les TABLES. Elles ne sont jamais renvoyées telles
quelles par l'API : on passe toujours par un schéma Pydantic (app/schemas).
"""
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    Genre, ModeLivraison, ModePaiement, Role, StatutCommande, StatutLivraison,
)
from app.utils import aujourdhui, maintenant


def _enum(cls):
    """Enum stocké en VARCHAR (plus simple à migrer qu'un type natif PostgreSQL)."""
    return Enum(cls, native_enum=False, length=20, validate_strings=True)


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nom_complet: Mapped[str] = mapped_column(String(150))
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), index=True)
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    adresse: Mapped[str | None] = mapped_column(String(255))
    genre: Mapped[Genre | None] = mapped_column(_enum(Genre))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=maintenant, onupdate=maintenant
    )

    # Supprimer un client supprime ses mesures (le service interdit déjà la
    # suppression s'il a des commandes : RG4).
    mesures: Mapped[list["Mesure"]] = relationship(
        back_populates="client", cascade="all, delete-orphan",
        order_by="Mesure.date_prise.desc(), Mesure.id.desc()",
    )
    commandes: Mapped[list["Commande"]] = relationship(back_populates="client")

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}"


class Mesure(Base):
    __tablename__ = "mesures"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    date_prise: Mapped[date] = mapped_column(Date, default=aujourdhui)
    prise_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    # 18 mesures facultatives, en centimètres
    taille_cm: Mapped[float | None] = mapped_column(Float)
    tour_cou: Mapped[float | None] = mapped_column(Float)
    carrure_dos: Mapped[float | None] = mapped_column(Float)
    longueur_epaule: Mapped[float | None] = mapped_column(Float)
    tour_poitrine: Mapped[float | None] = mapped_column(Float)
    tour_taille: Mapped[float | None] = mapped_column(Float)
    tour_bassin: Mapped[float | None] = mapped_column(Float)
    longueur_manche: Mapped[float | None] = mapped_column(Float)
    tour_bras: Mapped[float | None] = mapped_column(Float)
    tour_poignet: Mapped[float | None] = mapped_column(Float)
    longueur_dos: Mapped[float | None] = mapped_column(Float)
    longueur_haut: Mapped[float | None] = mapped_column(Float)
    longueur_pantalon: Mapped[float | None] = mapped_column(Float)
    tour_cuisse: Mapped[float | None] = mapped_column(Float)
    tour_genou: Mapped[float | None] = mapped_column(Float)
    bas_pantalon: Mapped[float | None] = mapped_column(Float)
    entrejambe: Mapped[float | None] = mapped_column(Float)
    longueur_robe: Mapped[float | None] = mapped_column(Float)

    client: Mapped[Client] = relationship(back_populates="mesures")


# Liste des 18 champs de mesure (utilisée par les schémas et le service)
CHAMPS_MESURES = [
    "taille_cm", "tour_cou", "carrure_dos", "longueur_epaule", "tour_poitrine",
    "tour_taille", "tour_bassin", "longueur_manche", "tour_bras", "tour_poignet",
    "longueur_dos", "longueur_haut", "longueur_pantalon", "tour_cuisse",
    "tour_genou", "bas_pantalon", "entrejambe", "longueur_robe",
]


class TypeVetement(Base):
    """Catalogue des prestations."""
    __tablename__ = "types_vetement"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    prix_base: Mapped[int] = mapped_column(Integer)  # FCFA
    delai_jours: Mapped[int] = mapped_column(Integer)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Commande(Base):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id"))
    statut: Mapped[StatutCommande] = mapped_column(
        _enum(StatutCommande), default=StatutCommande.en_attente, index=True
    )
    date_commande: Mapped[date] = mapped_column(Date, default=aujourdhui, index=True)
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    remise: Mapped[int] = mapped_column(Integer, default=0)
    montant_total: Mapped[int] = mapped_column(Integer, default=0)
    montant_paye: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=maintenant, onupdate=maintenant
    )

    client: Mapped[Client] = relationship(back_populates="commandes")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="LigneCommande.id"
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="Paiement.id"
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan",
        order_by="HistoriqueStatut.id",
    )
    livraison: Mapped["Livraison | None"] = relationship(
        back_populates="commande", cascade="all, delete-orphan", uselist=False
    )

    # --- Valeurs calculées (jamais saisies par le client de l'API) ---
    @property
    def solde(self) -> int:
        return self.montant_total - self.montant_paye

    @property
    def montant_prestations(self) -> int:
        return sum(ligne.quantite * ligne.prix_unitaire for ligne in self.lignes)

    @property
    def en_retard(self) -> bool:
        """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
        return (
            self.date_livraison_prevue < aujourdhui()
            and self.statut not in (StatutCommande.livree, StatutCommande.annulee)
        )

    @property
    def client_nom(self) -> str:
        return self.client.nom_complet


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(String(255))
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix_unitaire: Mapped[int] = mapped_column(Integer)

    commande: Mapped[Commande] = relationship(back_populates="lignes")
    type_vetement: Mapped[TypeVetement] = relationship()

    @property
    def sous_total(self) -> int:
        return self.quantite * self.prix_unitaire

    @property
    def type_vetement_nom(self) -> str:
        return self.type_vetement.nom


class HistoriqueStatut(Base):
    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    ancien_statut: Mapped[StatutCommande | None] = mapped_column(_enum(StatutCommande))
    nouveau_statut: Mapped[StatutCommande] = mapped_column(_enum(StatutCommande))
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    commande: Mapped[Commande] = relationship(back_populates="historique")


class Paiement(Base):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    montant: Mapped[int] = mapped_column(Integer)
    mode: Mapped[ModePaiement] = mapped_column(_enum(ModePaiement))
    reference: Mapped[str | None] = mapped_column(String(100))
    date_paiement: Mapped[date] = mapped_column(Date, default=aujourdhui, index=True)
    enregistre_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    commande: Mapped[Commande] = relationship(back_populates="paiements")


class Livraison(Base):
    __tablename__ = "livraisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True : une seule livraison par commande
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), unique=True
    )
    mode: Mapped[ModeLivraison] = mapped_column(_enum(ModeLivraison))
    adresse: Mapped[str | None] = mapped_column(String(255))
    livreur: Mapped[str | None] = mapped_column(String(100))
    date_prevue: Mapped[date] = mapped_column(Date, index=True)
    date_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[StatutLivraison] = mapped_column(
        _enum(StatutLivraison), default=StatutLivraison.planifiee
    )
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped[Commande] = relationship(back_populates="livraison")

    @property
    def numero_commande(self) -> str:
        return self.commande.numero

    @property
    def client_nom(self) -> str:
        return self.commande.client.nom_complet

    @property
    def client_telephone(self) -> str:
        return self.commande.client.telephone

    @property
    def solde_commande(self) -> int:
        return self.commande.solde
