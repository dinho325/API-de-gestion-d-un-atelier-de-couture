"""Initialisation : `python -m app.seed`

Crée (sans doublon, on peut le relancer) :
- le premier administrateur, à partir de ADMIN_EMAIL / ADMIN_PASSWORD ;
- les prestations du catalogue de départ (annexe B) ;
- si SEED_DEMO_USERS=true : un compte accueil et un compte tailleur de démonstration.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.enums import Role
from app.models import TypeVetement, Utilisateur
from app.security import hasher_mot_de_passe

CATALOGUE = [
    ("Boubou", "Boubou homme en bazin ou brodé", 35000, 10),
    ("Costume 2 pièces", "Veste et pantalon", 85000, 14),
    ("Robe", "Robe sur mesure", 30000, 7),
    ("Ensemble wax", "Tenue deux pièces en wax", 25000, 7),
    ("Chemise", "Chemise sur mesure", 15000, 5),
    ("Pantalon", "Pantalon sur mesure", 12000, 4),
    ("Retouche", "Ourlet, rétrécissement, remplacement de fermeture", 3000, 2),
]


def _creer_utilisateur(db: Session, email: str, mot_de_passe: str, nom: str, role: Role) -> None:
    email = email.lower()
    if db.scalar(select(Utilisateur.id).where(Utilisateur.email == email)):
        print(f"= compte déjà présent : {email}")
        return
    db.add(Utilisateur(
        email=email, nom_complet=nom, role=role, actif=True,
        mot_de_passe_hash=hasher_mot_de_passe(mot_de_passe),
    ))
    print(f"+ compte créé : {email} ({role.value})")


def seed(db: Session) -> None:
    if settings.admin_email and settings.admin_password:
        _creer_utilisateur(db, settings.admin_email, settings.admin_password, settings.admin_nom, Role.admin)
    else:
        print("! ADMIN_EMAIL / ADMIN_PASSWORD absents : aucun administrateur créé.")

    if settings.seed_demo_users and settings.demo_password:
        _creer_utilisateur(db, "accueil@atelier.sn", settings.demo_password, "Awa (accueil)", Role.accueil)
        _creer_utilisateur(db, "tailleur@atelier.sn", settings.demo_password, "Ibrahima (tailleur)", Role.tailleur)

    for nom, description, prix, delai in CATALOGUE:
        if db.scalar(select(TypeVetement.id).where(TypeVetement.nom == nom)):
            continue
        db.add(TypeVetement(nom=nom, description=description, prix_base=prix, delai_jours=delai, actif=True))
        print(f"+ prestation créée : {nom}")
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
