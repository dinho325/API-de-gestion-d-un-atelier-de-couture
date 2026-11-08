"""Scénario de démonstration (annexe A de l'énoncé), rejouable automatiquement.

Usage contre un serveur lancé :
    python -m scripts.scenario_demo http://localhost:8000

Utilise les comptes créés par `python -m app.seed` (SEED_DEMO_USERS=true).
Chaque étape vérifie le résultat attendu avec un assert.
"""
import sys
from datetime import date, timedelta

API = "/api/v1"


def jouer(http, comptes: dict[str, tuple[str, str]], afficher=print) -> None:
    """`http` : client httpx ou TestClient. `comptes` : {role: (email, mot_de_passe)}."""

    def connecter(role: str) -> dict:
        email, mdp = comptes[role]
        r = http.post(f"{API}/auth/login", data={"username": email, "password": mdp})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def etape(texte: str):
        afficher(f"✔ {texte}")

    accueil, tailleur, admin = connecter("accueil"), connecter("tailleur"), connecter("admin")

    # ---- 1. Accueil : création de la cliente, doublon refusé
    r = http.post(f"{API}/clients", headers=accueil,
                  json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"})
    if r.status_code == 409:   # scénario rejoué sur une base déjà utilisée
        fatou = http.get(f"{API}/clients?q=771234567", headers=accueil).json()["items"][0]
    else:
        assert r.status_code == 201, r.text
        fatou = r.json()
    r = http.post(f"{API}/clients", headers=accueil, json={"nom": "Autre", "prenom": "Client", "telephone": "771234567"})
    assert r.status_code == 409, r.text
    etape("1. Cliente créée ; le doublon « 771234567 » est refusé (409)")

    # ---- 2. Tailleur : mesures ; l'accueil reçoit 403
    r = http.post(f"{API}/clients/{fatou['id']}/mesures", headers=tailleur,
                  json={"tour_poitrine": 92, "tour_taille": 74, "tour_bassin": 100, "longueur_robe": 110})
    assert r.status_code == 201, r.text
    mesure = r.json()
    r = http.post(f"{API}/clients/{fatou['id']}/mesures", headers=accueil, json={"tour_taille": 74})
    assert r.status_code == 403, r.text
    etape("2. Mesures prises par le tailleur ; l'accueil reçoit 403")

    # ---- 3. Accueil : commande
    catalogue = {p["nom"]: p["id"] for p in http.get(f"{API}/catalogue", headers=accueil).json()}
    avant = http.get(f"{API}/statistiques/tableau-de-bord", headers=admin).json()
    r = http.post(f"{API}/commandes", headers=accueil, json={
        "client_id": fatou["id"], "remise": 5000,
        "lignes": [{"type_vetement_id": catalogue["Boubou"], "quantite": 2},
                   {"type_vetement_id": catalogue["Pantalon"], "quantite": 1, "prix_unitaire": 10000}]})
    assert r.status_code == 201, r.text
    cmd = r.json()
    assert cmd["numero"] == f"CMD-{date.today().year}-{cmd['id']:05d}"
    assert cmd["montant_total"] == 75000 and cmd["statut"] == "en_attente"
    assert cmd["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert cmd["mesure_id"] == mesure["id"]
    etape(f"3. Commande {cmd['numero']} : total 75 000 FCFA, livraison prévue le "
          f"{cmd['date_livraison_prevue']}, mesures rattachées automatiquement")

    # ---- 4. Transition interdite
    r = http.post(f"{API}/commandes/{cmd['id']}/statut", headers=accueil, json={"statut": "terminee"})
    assert r.status_code == 409 and "Statuts possibles : annulee, en_coupe" in r.json()["detail"], r.text
    etape(f"4. en_attente → terminee refusé (409) : {r.json()['detail']}")

    # ---- 5. Tailleur : production complète
    for s in ("en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"):
        r = http.post(f"{API}/commandes/{cmd['id']}/statut", headers=tailleur, json={"statut": s})
        assert r.status_code == 200, r.text
    histo = http.get(f"{API}/commandes/{cmd['id']}/historique", headers=tailleur).json()
    assert [h["nouveau_statut"] for h in histo][-1] == "terminee" and len(histo) == 7
    etape("5. Production jusqu'à « terminee » (aller-retour essayage/retouches), historique de 7 lignes")

    # ---- 6. Acompte Wave ; paiement trop élevé refusé
    r = http.post(f"{API}/commandes/{cmd['id']}/paiements", headers=accueil,
                  json={"montant": 30000, "mode": "wave", "reference": "WV-DEMO-001"})
    assert r.status_code == 201, r.text
    r = http.post(f"{API}/commandes/{cmd['id']}/paiements", headers=accueil, json={"montant": 50000, "mode": "wave"})
    assert r.status_code == 409, r.text
    etape("6. Acompte Wave de 30 000 FCFA encaissé ; paiement de 50 000 > solde refusé (409)")

    # ---- 7. Livraison refusée : solde impayé
    r = http.post(f"{API}/commandes/{cmd['id']}/livraison/confirmer", headers=accueil)
    assert r.status_code == 409, r.text
    etape(f"7. Livraison refusée (409) : {r.json()['detail']}")

    # ---- 8. Solde puis livraison
    r = http.post(f"{API}/commandes/{cmd['id']}/paiements", headers=accueil, json={"montant": 45000, "mode": "especes"})
    assert r.status_code == 201, r.text
    r = http.post(f"{API}/commandes/{cmd['id']}/livraison/confirmer", headers=accueil)
    assert r.status_code == 200 and r.json()["statut"] == "livree" and r.json()["solde"] == 0, r.text
    etape("8. Solde encaissé, livraison confirmée : commande « livree », solde 0")

    # ---- 9. Tableau de bord admin ; accueil refusé
    apres = http.get(f"{API}/statistiques/tableau-de-bord", headers=admin).json()
    assert apres["chiffre_affaires_mois"] - avant["chiffre_affaires_mois"] == 75000
    r = http.get(f"{API}/statistiques/tableau-de-bord", headers=accueil)
    assert r.status_code == 403, r.text
    etape("9. Le chiffre d'affaires du mois a augmenté de 75 000 FCFA ; l'accueil reçoit 403")

    # ---- 10. Impayés et retards
    impayes = http.get(f"{API}/statistiques/impayes", headers=admin)
    retards = http.get(f"{API}/commandes?en_retard=true", headers=admin)
    assert impayes.status_code == 200 and retards.status_code == 200
    etape(f"10. Impayés : {impayes.json()['total']} commande(s) ; en retard : {retards.json()['total']} commande(s)")


if __name__ == "__main__":
    import httpx

    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    # Comptes du seed (voir README) — le mot de passe de démo vient de .env.example par défaut
    from app.config import settings

    comptes = {
        "admin": (settings.admin_email, settings.admin_password),
        "accueil": ("accueil@atelier.sn", settings.demo_password),
        "tailleur": ("tailleur@atelier.sn", settings.demo_password),
    }
    with httpx.Client(base_url=base, timeout=30) as client:
        jouer(client, comptes)
    print("\nScénario de démonstration réussi ✔")
