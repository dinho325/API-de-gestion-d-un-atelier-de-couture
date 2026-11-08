from datetime import date, timedelta

from app.models import Commande

API = "/api/v1"


def test_tableau_de_bord(http, auth, db, faire_commande, avancer):
    a = faire_commande(lignes=[("Boubou", 2)])            # 70 000
    b = faire_commande(lignes=[("Pantalon", 1)])          # 12 000
    annulee = faire_commande(lignes=[("Robe", 1)])        # annulée : exclue
    http.post(f"{API}/commandes/{annulee['id']}/statut", headers=auth["accueil"], json={"statut": "annulee"})
    http.post(f"{API}/commandes/{a['id']}/paiements", headers=auth["accueil"], json={"montant": 20000, "mode": "wave"})
    avancer(b["id"], "en_coupe", "en_couture", "terminee")
    commande = db.get(Commande, a["id"])
    commande.date_livraison_prevue = date.today() - timedelta(days=2)    # en retard
    db.commit()

    t = http.get(f"{API}/statistiques/tableau-de-bord", headers=auth["admin"]).json()
    assert t["chiffre_affaires_mois"] == 82000 and t["encaisse_mois"] == 20000
    assert t["nb_commandes_mois"] == 2 and t["reste_a_encaisser"] == 62000
    assert t["nb_commandes_en_retard"] == 1 and t["commandes_pretes_a_livrer"] == 1
    assert t["commandes_par_statut"]["en_attente"] == 1 and t["commandes_par_statut"]["terminee"] == 1
    assert t["commandes_par_statut"]["annulee"] == 1 and t["commandes_par_statut"]["livree"] == 0
    assert set(t["commandes_par_statut"]) == {"en_attente", "en_coupe", "en_couture", "essayage",
                                              "retouches", "terminee", "livree", "annulee"}
    assert t["livraisons_du_jour"] == 0


def test_chiffre_affaires_par_jour_et_par_mois(http, auth, db, faire_commande):
    a, b = faire_commande(lignes=[("Boubou", 1)]), faire_commande(lignes=[("Pantalon", 1)])
    http.post(f"{API}/commandes/{a['id']}/paiements", headers=auth["accueil"], json={"montant": 5000, "mode": "especes"})
    ancienne = db.get(Commande, b["id"])
    ancienne.date_commande = date(2026, 1, 15)
    db.commit()
    jour = http.get(f"{API}/statistiques/chiffre-affaires?granularite=jour&date_debut=2026-01-01&date_fin={date.today()}",
                    headers=auth["admin"]).json()
    assert [p["periode"] for p in jour["periodes"]] == ["2026-01-15", date.today().isoformat()]
    assert jour["periodes"][0]["chiffre_affaires"] == 12000 and jour["periodes"][1]["encaisse"] == 5000
    mois = http.get(f"{API}/statistiques/chiffre-affaires?granularite=mois&date_debut=2026-01-01&date_fin={date.today()}",
                    headers=auth["admin"]).json()
    assert mois["periodes"][0]["periode"] == "2026-01" and mois["total_chiffre_affaires"] == 47000


def test_chiffre_affaires_periode_incoherente_422(http, auth):
    r = http.get(f"{API}/statistiques/chiffre-affaires?date_debut=2026-05-02&date_fin=2026-05-01", headers=auth["admin"])
    assert r.status_code == 422


def test_types_vetement_et_top_clients(http, auth, faire_commande):
    c1 = faire_commande(lignes=[("Boubou", 2), ("Pantalon", 1)], remise=5000)
    faire_commande(lignes=[("Pantalon", 3)])
    http.post(f"{API}/commandes/{c1['id']}/paiements", headers=auth["accueil"], json={"montant": 30000, "mode": "wave"})
    types = http.get(f"{API}/statistiques/types-vetement", headers=auth["admin"]).json()
    assert [(t["nom"], t["quantite"], t["chiffre_affaires"]) for t in types] == [
        ("Boubou", 2, 70000), ("Pantalon", 4, 48000)]     # avant remise
    top = http.get(f"{API}/statistiques/top-clients?limite=5", headers=auth["admin"]).json()
    assert len(top) == 1 and top[0]["nb_commandes"] == 2
    assert top[0]["chiffre_affaires"] == 77000 + 36000 and top[0]["solde_du"] == 113000 - 30000
    assert top[0]["client_nom"] == "Fatou Diop"


def test_impayes_les_plus_urgents_dabord(http, auth, db, faire_commande):
    a = faire_commande(lignes=[("Boubou", 1)])
    b = faire_commande(lignes=[("Pantalon", 1)])
    soldee = faire_commande(lignes=[("Chemise", 1)])
    http.post(f"{API}/commandes/{soldee['id']}/paiements", headers=auth["accueil"], json={"montant": 15000, "mode": "wave"})
    db.get(Commande, b["id"]).date_livraison_prevue = date.today() + timedelta(days=1)
    db.commit()
    r = http.get(f"{API}/statistiques/impayes", headers=auth["admin"]).json()
    assert r["total"] == 2 and [c["id"] for c in r["items"]] == [b["id"], a["id"]]
