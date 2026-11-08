"""Fixtures communes. Les tests utilisent SQLite en mémoire (seul usage toléré de
SQLite) : ils sont rapides et ne touchent jamais à la vraie base PostgreSQL."""
import os

# Ces variables doivent être posées AVANT d'importer l'application.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "secret-de-test-uniquement"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.enums import Role
from app.main import app
from app.models import TypeVetement, Utilisateur
from app.security import creer_jeton, hasher_mot_de_passe
from app.seed import CATALOGUE

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, expire_on_commit=False)
MOT_DE_PASSE = "motdepasse123"
HASH = hasher_mot_de_passe(MOT_DE_PASSE)  # calculé une seule fois (Argon2 est volontairement lent)


def _get_db_test():
    with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _get_db_test


@pytest.fixture(autouse=True)
def base_propre():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with TestSession() as session:
        yield session


@pytest.fixture
def http():
    return TestClient(app)


@pytest.fixture
def utilisateurs(db):
    """Un compte par rôle (+ un second admin)."""
    comptes = {}
    for cle, role in (("admin", Role.admin), ("accueil", Role.accueil),
                      ("tailleur", Role.tailleur), ("admin2", Role.admin)):
        u = Utilisateur(email=f"{cle}@atelier.sn", nom_complet=cle.capitalize(),
                        role=role, actif=True, mot_de_passe_hash=HASH)
        db.add(u)
        comptes[cle] = u
    db.commit()
    return comptes


@pytest.fixture
def auth(utilisateurs):
    """En-têtes Authorization par rôle : auth['admin'], auth['accueil'], auth['tailleur']."""
    return {cle: {"Authorization": f"Bearer {creer_jeton(u.id)[0]}"} for cle, u in utilisateurs.items()}


@pytest.fixture
def catalogue(db):
    """Catalogue de l'annexe B ; renvoie {nom: id}."""
    ids = {}
    for nom, description, prix, delai in CATALOGUE:
        p = TypeVetement(nom=nom, description=description, prix_base=prix, delai_jours=delai, actif=True)
        db.add(p)
        db.flush()
        ids[nom] = p.id
    db.commit()
    return ids


# ----------------------------------------------------------- aides de test
@pytest.fixture
def client_fatou(http, auth):
    r = http.post("/api/v1/clients", headers=auth["accueil"],
                  json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def mesure_fatou(http, auth, client_fatou):
    r = http.post(f"/api/v1/clients/{client_fatou['id']}/mesures", headers=auth["tailleur"],
                  json={"tour_poitrine": 92, "tour_taille": 74})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def faire_commande(http, auth, client_fatou, catalogue):
    """Fabrique de commandes : faire_commande(lignes=[("Boubou", 2)], remise=0, **extra)."""
    def _faire(lignes=(("Boubou", 2),), remise=0, **extra):
        corps = {
            "client_id": client_fatou["id"], "remise": remise,
            "lignes": [{"type_vetement_id": catalogue[nom], "quantite": q} for nom, q in lignes],
            **extra,
        }
        r = http.post("/api/v1/commandes", headers=auth["accueil"], json=corps)
        assert r.status_code == 201, r.text
        return r.json()
    return _faire


@pytest.fixture
def avancer(http, auth):
    """avancer(commande_id, 'en_coupe', 'en_couture', ...) enchaîne les statuts (tailleur)."""
    def _avancer(commande_id, *statuts):
        for s in statuts:
            r = http.post(f"/api/v1/commandes/{commande_id}/statut", headers=auth["tailleur"], json={"statut": s})
            assert r.status_code == 200, r.text
    return _avancer
