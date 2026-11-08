API = "/api/v1"


def test_mesure_creee_par_le_tailleur_connecte(http, auth, utilisateurs, client_fatou):
    r = http.post(f"{API}/clients/{client_fatou['id']}/mesures", headers=auth["tailleur"],
                  json={"tour_cou": 38.5, "notes": "Prise du matin"})
    assert r.status_code == 201
    assert r.json()["prise_par_id"] == utilisateurs["tailleur"].id
    assert r.json()["date_prise"] is not None and r.json()["tour_taille"] is None


def test_au_moins_une_mesure_422(http, auth, client_fatou):  # RG2
    r = http.post(f"{API}/clients/{client_fatou['id']}/mesures", headers=auth["tailleur"], json={"notes": "vide"})
    assert r.status_code == 422


def test_mesure_positive_et_max_300_422(http, auth, client_fatou):  # RG2
    url = f"{API}/clients/{client_fatou['id']}/mesures"
    assert http.post(url, headers=auth["tailleur"], json={"tour_cou": 0}).status_code == 422
    assert http.post(url, headers=auth["tailleur"], json={"tour_cou": -5}).status_code == 422
    assert http.post(url, headers=auth["tailleur"], json={"tour_cou": 300.1}).status_code == 422
    assert http.post(url, headers=auth["tailleur"], json={"tour_cou": 300}).status_code == 201


def test_historique_et_dernieres_mesures(http, auth, client_fatou):  # RG3
    url = f"{API}/clients/{client_fatou['id']}/mesures"
    http.post(url, headers=auth["tailleur"], json={"tour_taille": 70, "date_prise": "2026-01-10"})
    recente = http.post(url, headers=auth["tailleur"], json={"tour_taille": 72, "date_prise": "2026-03-10"}).json()
    http.post(url, headers=auth["tailleur"], json={"tour_taille": 68, "date_prise": "2025-12-01"})
    historique = http.get(url, headers=auth["accueil"]).json()
    assert [m["date_prise"] for m in historique] == ["2026-03-10", "2026-01-10", "2025-12-01"]
    assert http.get(f"{url}/derniere", headers=auth["accueil"]).json()["id"] == recente["id"]


def test_derniere_mesure_404_si_aucune(http, auth, client_fatou):
    assert http.get(f"{API}/clients/{client_fatou['id']}/mesures/derniere", headers=auth["accueil"]).status_code == 404


def test_correction_de_mesure(http, auth, mesure_fatou):
    url = f"{API}/mesures/{mesure_fatou['id']}"
    r = http.patch(url, headers=auth["tailleur"], json={"tour_poitrine": 95})
    assert r.status_code == 200 and r.json()["tour_poitrine"] == 95 and r.json()["tour_taille"] == 74


def test_correction_qui_supprimerait_toutes_les_mesures_422(http, auth, mesure_fatou):
    url = f"{API}/mesures/{mesure_fatou['id']}"
    r = http.patch(url, headers=auth["tailleur"], json={"tour_poitrine": None, "tour_taille": None})
    assert r.status_code == 422
    assert http.get(url, headers=auth["tailleur"]).json()["tour_poitrine"] == 92  # rien n'a changé


def test_commande_utilise_les_dernieres_mesures_par_defaut(http, auth, client_fatou, mesure_fatou, faire_commande):  # RG9
    assert faire_commande()["mesure_id"] == mesure_fatou["id"]


def test_mesure_utilisee_par_une_commande_non_supprimable_409(http, auth, mesure_fatou, faire_commande):  # RG4
    faire_commande()
    assert http.delete(f"{API}/mesures/{mesure_fatou['id']}", headers=auth["tailleur"]).status_code == 409


def test_suppression_mesure_libre(http, auth, mesure_fatou):
    assert http.delete(f"{API}/mesures/{mesure_fatou['id']}", headers=auth["tailleur"]).status_code == 204
    assert http.get(f"{API}/mesures/{mesure_fatou['id']}", headers=auth["tailleur"]).status_code == 404
