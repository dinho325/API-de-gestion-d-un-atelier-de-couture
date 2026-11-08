# Atelier de couture — API de gestion (FastAPI + PostgreSQL)

API REST pour l'atelier de Mamadou, tailleur à Dakar
(clients, mesures, commandes, paiements, livraisons, statistiques).

Stack : Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic · Pydantic v2 · JWT (PyJWT) · Argon2 · pytest · Docker.

## 1. Lancement rapide (Docker)

```bash
cp .env.example .env         
docker compose up --build
```

Au démarrage, le conteneur de l'API exécute automatiquement `alembic upgrade head`, puis
`python -m app.seed`, puis lance le serveur.

- Documentation interactive (Swagger) : <http://localhost:8000/docs>
- Santé : <http://localhost:8000/health>

## 2. Lancement en local (sans Docker pour l'API)

```bash
python -m venv venv && source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 
alembic upgrade head                                  
python -m app.seed                                    
uvicorn app.main:app --reload
```

Pour n'avoir que la base dans Docker : `docker compose up db -d` (puis `DATABASE_URL=...@localhost:5432/...`
et, dans `docker-compose.yml`, ajoutez `ports: ["5432:5432"]` au service `db`).

## 3. Comptes de test (créés par `python -m app.seed`)

| Rôle | E-mail | Mot de passe |
|---|---|---|
| admin | valeur de `ADMIN_EMAIL` (.env.example : `patron@atelier.sn`) | valeur de `ADMIN_PASSWORD` |
| accueil | `accueil@atelier.sn` | valeur de `DEMO_PASSWORD` |
| tailleur | `tailleur@atelier.sn` | valeur de `DEMO_PASSWORD` |

Les comptes accueil/tailleur n'existent que si `SEED_DEMO_USERS=true`. Le seed est rejouable (aucun doublon).
Dans Swagger : bouton **Authorize**, `username` = e-mail.

## 4. Tests

```bash
pytest -q
```

Les tests utilisent SQLite **en mémoire** (jamais la vraie base) : aucun PostgreSQL requis.
Ils couvrent les règles de gestion, la matrice des droits par rôle et le scénario de démonstration.

### Rejouer le scénario de démonstration (annexe A) sur un serveur lancé

```bash
python -m scripts.scenario_demo http://localhost:8000
```

## 5. Architecture

```
app/
  main.py            assemble l'application, gère les erreurs {"detail": "..."} et /health
  config.py          variables d'environnement (.env)
  database.py        moteur, session, Base
  models.py          modèles SQLAlchemy 2 (tables)
  schemas/           schémas Pydantic : Create / Update / Lecture, séparés des modèles
  routers/           un fichier par domaine : droits -> service -> commit
  services/          TOUTE la logique métier (testable sans HTTP)
  deps.py            utilisateur connecté + contrôle des rôles
  security.py        Argon2 + JWT
  errors.py          erreurs métier (Conflit 409, DonneeInvalide 422...)
  seed.py            python -m app.seed
alembic/             migrations (schéma initial complet)
tests/               pytest + TestClient
scripts/             scénario de démonstration
```

Principe : une route **ne contient aucune règle de gestion**. Elle vérifie les droits (dépendance),
appelle un service, fait `commit()`, et renvoie un schéma de lecture. Les services lèvent des
`ErreurMetier` ; un gestionnaire global les convertit en `{"detail": "message en français"}`.

## 6. Où est codée chaque règle de gestion ?

| Règle | Où | Test |
|---|---|---|
| RG1 téléphone normalisé / unique | `utils.normaliser_telephone`, `schemas/client.py`, `services/clients.py` | `test_clients_catalogue`, `test_unitaires_services` |
| RG2 mesures facultatives, ≥ 1, 0 < x ≤ 300 | `schemas/mesure.py`, `services/mesures.py` | `test_mesures` |
| RG3 historique / dernières mesures | `services/mesures.py` | `test_mesures` |
| RG4 suppressions interdites | `services/clients.py`, `services/mesures.py` | `test_clients_catalogue`, `test_mesures` |
| RG5 numéro `CMD-AAAA-NNNNN` | `services/commandes.creer_commande` | `test_commandes` |
| RG6 prix par défaut, prestation inactive | `services/commandes._construire_ligne` | `test_commandes` |
| RG7 montants calculés par le serveur | `services/commandes.recalculer_montants` | `test_unitaires_services`, `test_commandes` |
| RG8 date de livraison par défaut | `services/commandes.creer_commande` | `test_commandes` |
| RG9 mesures du bon client / dernières par défaut | `services/commandes._mesure_du_client` | `test_commandes`, `test_mesures` |
| RG10 lignes modifiables en `en_attente` | `services/commandes._verifier_lignes_modifiables` | `test_commandes` |
| RG11 commande en retard | `models.Commande.en_retard`, `services/commandes.condition_en_retard` | `test_commandes` |
| RG12 livrée/annulée non modifiable | `services/commandes.verifier_modifiable` | `test_commandes` |
| RG13-15 workflow, annulation, historique | `services/commandes.TRANSITIONS`, `changer_statut` | `test_commandes` |
| RG16-17 paiements | `services/paiements.py` | `test_paiements_livraisons` |
| RG18-20 livraisons | `services/livraisons.py` | `test_paiements_livraisons` |
| RG21 Argon2, jamais renvoyé, ≥ 8 caractères | `security.py`, `schemas/utilisateur.py` | `test_auth_utilisateurs` |
| RG22 JWT expirant, compte désactivé refusé | `security.py`, `deps.utilisateur_courant` | `test_auth_utilisateurs` |
| RG23 même message de connexion | `services/utilisateurs.authentifier` | `test_auth_utilisateurs` |
| RG24 admin ne se retire pas ses droits | `services/utilisateurs.modifier_utilisateur` | `test_auth_utilisateurs` |
| Statistiques (définitions) | `services/statistiques.py` | `test_statistiques` |

## 7. Routes réalisées (44 sur 44) — préfixe `/api/v1`

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 1 | POST | `/auth/login` | public |
| 2 | GET | `/auth/me` | connecté |
| 3-6 | POST, GET, GET, PATCH | `/utilisateurs`, `/utilisateurs/{id}` | admin |
| 7-13 | POST, GET, GET, PATCH, DELETE, GET, GET | `/clients`, `/clients/{id}`, `/clients/{id}/commandes`, `/clients/{id}/resume` | tous (DELETE : admin) |
| 14-17 | POST, GET, GET, PATCH | `/catalogue`, `/catalogue/{id}` | lecture : tous · écriture : admin |
| 18-23 | POST, GET, GET, GET, PATCH, DELETE | `/clients/{id}/mesures`, `/clients/{id}/mesures/derniere`, `/mesures/{id}` | lecture : tous · écriture : tailleur |
| 24-31 | POST, GET, GET, PATCH, POST, GET, POST, DELETE | `/commandes`, `/commandes/{id}`, `/commandes/{id}/statut`, `/commandes/{id}/historique`, `/commandes/{id}/lignes`, `/commandes/{id}/lignes/{ligne_id}` | création/modification/lignes : accueil · statut : tous (RG13-14) · lecture : tous |
| 32-34 | POST, GET, DELETE | `/commandes/{id}/paiements`, `/paiements/{id}` | encaisser : accueil · annuler : admin · lecture : tous |
| 35-38 | PUT, GET, POST, GET | `/commandes/{id}/livraison`, `/commandes/{id}/livraison/confirmer`, `/livraisons` | écriture : accueil · lecture : tous |
| 39-43 | GET ×5 | `/statistiques/tableau-de-bord`, `/chiffre-affaires`, `/types-vetement`, `/top-clients`, `/impayes` | admin |
| 44 | GET | `/health` (hors préfixe) | public |

L'administrateur peut effectuer toutes les actions des autres rôles.

> Note : dans le PDF de l'énoncé, les chemins des statistiques sont coupés en fin de ligne
> (« tableau-debord », « chiffreaffaires », « typesvetement »). Ils sont implémentés avec leurs
> tirets : `/statistiques/tableau-de-bord`, `/statistiques/chiffre-affaires`, `/statistiques/types-vetement`.
> Si votre enseignant attend une autre orthographe, il suffit de changer le chemin dans `routers/statistiques.py`.

## 8. Choix d'implémentation à connaître

- **Listes paginées** (`{"items","total","limit","offset"}`) : clients, commandes (et celles d'un client), impayés.
  Les autres listes (utilisateurs, catalogue, mesures, paiements, livraisons) sont des tableaux simples, comme dans l'énoncé.
- **Annuler une commande** : possible depuis `en_attente`, `en_coupe`, `en_couture`, `essayage`, `retouches`
  (pas depuis `terminee`, conformément au tableau des transitions).
- **Nombre de commandes du mois** (tableau de bord) : commandes non annulées, comme le chiffre d'affaires.
- **Encaissé** : inclut tous les paiements reçus, y compris sur une commande annulée ensuite (l'argent a bien été reçu).
- **Enums** stockés en `VARCHAR` (et non en type natif PostgreSQL) pour faciliter les migrations.
- **Erreurs 422** : message unique en français listant les champs invalides.
- Le champ « numero et mot de passe » de l'énoncé : la connexion se fait avec l'**e-mail** (route 1 : `username` = email).
- Les montants sont des entiers FCFA ; les mesures des nombres décimaux en cm.

## 9. Vérification avant remise

Clonez le dépôt dans un dossier vide, suivez uniquement ce README, puis lancez `pytest`.
