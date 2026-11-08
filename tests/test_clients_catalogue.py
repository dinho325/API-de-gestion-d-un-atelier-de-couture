API = "/api/v1"


def creer(http, auth, **champs):
    corps = {"nom": "Ndiaye", "prenom": "Moussa", "telephone": "78 000 00 01", **champs}
    return http.post(f"{API}/clients", headers=auth["accueil"], json=corps)


def test_telephone_normalise_et_doublon_409(http, auth, client_fatou):  # RG1
    assert client_fatou["telephone"] == "771234567"
    r = creer(http, auth, telephone="771234567")
    assert r.status_code == 409
    assert creer(http, auth, telephone="(77) 123.45.67").status_code == 409


def test_telephone_invalide_422(http, auth):
    assert creer(http, auth, telephone="abc").status_code == 422
    assert creer(http, auth, telephone="123").status_code == 422


def test_liste_paginee_triee_et_recherche(http, auth):
    for nom, prenom, tel in [("Sow", "Awa", "700000001"), ("Ba", "Zeynab", "700000002"),
                             ("Ba", "Amadou", "700000003")]:
        creer(http, auth, nom=nom, prenom=prenom, telephone=tel)
    r = http.get(f"{API}/clients", headers=auth["accueil"]).json()
    assert [(c["nom"], c["prenom"]) for c in r["items"]] == [("Ba", "Amadou"), ("Ba", "Zeynab"), ("Sow", "Awa")]
    assert r["total"] == 3 and r["limit"] == 20 and r["offset"] == 0
    p = http.get(f"{API}/clients?limit=1&offset=1", headers=auth["accueil"]).json()
    assert len(p["items"]) == 1 and p["total"] == 3
    assert http.get(f"{API}/clients?q=zey", headers=auth["accueil"]).json()["total"] == 1
    assert http.get(f"{API}/clients?q=0000000", headers=auth["accueil"]).json()["total"] == 3
    assert http.get(f"{API}/clients?q=a", headers=auth["accueil"]).status_code == 422  # 2 caractères minimum
    assert http.get(f"{API}/clients?limit=101", headers=auth["accueil"]).status_code == 422


def test_filtre_genre(http, auth):
    creer(http, auth, telephone="700000001", genre="homme")
    creer(http, auth, telephone="700000002", genre="femme")
    assert http.get(f"{API}/clients?genre=femme", headers=auth["accueil"]).json()["total"] == 1


def test_modification_partielle(http, auth, client_fatou):
    url = f"{API}/clients/{client_fatou['id']}"
    r = http.patch(url, headers=auth["accueil"], json={"adresse": "Médina, Dakar"})
    assert r.status_code == 200 and r.json()["adresse"] == "Médina, Dakar" and r.json()["nom"] == "Diop"
    # Garder son propre numéro n'est pas un doublon
    assert http.patch(url, headers=auth["accueil"], json={"telephone": "77 123 45 67"}).status_code == 200


def test_champs_obligatoires_non_videables(http, auth, client_fatou):
    url = f"{API}/clients/{client_fatou['id']}"
    for champ in ("nom", "prenom", "telephone"):
        assert http.patch(url, headers=auth["accueil"], json={champ: None}).status_code == 422
        assert http.patch(url, headers=auth["accueil"], json={champ: ""}).status_code == 422


def test_changer_pour_le_numero_dun_autre_client_409(http, auth, client_fatou):
    autre = creer(http, auth).json()
    r = http.patch(f"{API}/clients/{autre['id']}", headers=auth["accueil"], json={"telephone": "771234567"})
    assert r.status_code == 409


def test_client_inconnu_404(http, auth):
    assert http.get(f"{API}/clients/999", headers=auth["accueil"]).status_code == 404


def test_suppression_client_sans_commande_supprime_ses_mesures(http, auth, client_fatou, mesure_fatou):
    r = http.delete(f"{API}/clients/{client_fatou['id']}", headers=auth["admin"])
    assert r.status_code == 204
    assert http.get(f"{API}/mesures/{mesure_fatou['id']}", headers=auth["admin"]).status_code == 404


def test_suppression_client_avec_commandes_409(http, auth, client_fatou, faire_commande):  # RG4
    faire_commande()
    r = http.delete(f"{API}/clients/{client_fatou['id']}", headers=auth["admin"])
    assert r.status_code == 409


def test_resume_client_exclut_les_annulees(http, auth, client_fatou, faire_commande):
    c1 = faire_commande(lignes=[("Boubou", 1)])            # 35 000
    c2 = faire_commande(lignes=[("Pantalon", 1)])           # 12 000
    http.post(f"{API}/commandes/{c2['id']}/statut", headers=auth["accueil"], json={"statut": "annulee"})
    http.post(f"{API}/commandes/{c1['id']}/paiements", headers=auth["accueil"], json={"montant": 10000, "mode": "wave"})
    r = http.get(f"{API}/clients/{client_fatou['id']}/resume", headers=auth["tailleur"]).json()
    assert r["nb_commandes"] == 1 and r["chiffre_affaires"] == 35000
    assert r["total_paye"] == 10000 and r["solde_du"] == 25000
    assert r["a_des_mesures"] is False and r["derniere_commande"] is not None


def test_commandes_du_client_recente_en_premier(http, auth, client_fatou, faire_commande):
    a, b = faire_commande(), faire_commande()
    r = http.get(f"{API}/clients/{client_fatou['id']}/commandes", headers=auth["tailleur"]).json()
    assert [c["id"] for c in r["items"]] == [b["id"], a["id"]]


# ----------------------------------------------------------------- catalogue
def test_catalogue_creation_doublon_et_filtre_actifs(http, auth, catalogue):
    r = http.post(f"{API}/catalogue", headers=auth["admin"], json={"nom": "Veste", "prix_base": 40000, "delai_jours": 8})
    assert r.status_code == 201
    assert http.post(f"{API}/catalogue", headers=auth["admin"], json={"nom": "Veste", "prix_base": 1, "delai_jours": 1}).status_code == 409
    http.patch(f"{API}/catalogue/{r.json()['id']}", headers=auth["admin"], json={"actif": False})
    actifs = http.get(f"{API}/catalogue", headers=auth["tailleur"]).json()
    tous = http.get(f"{API}/catalogue?actifs_seulement=false", headers=auth["tailleur"]).json()
    assert "Veste" not in [p["nom"] for p in actifs] and "Veste" in [p["nom"] for p in tous]
    assert [p["nom"] for p in tous] == sorted(p["nom"] for p in tous)


def test_catalogue_modification_et_404(http, auth, catalogue):
    pid = catalogue["Boubou"]
    r = http.patch(f"{API}/catalogue/{pid}", headers=auth["admin"], json={"prix_base": 40000, "delai_jours": 12})
    assert r.json()["prix_base"] == 40000 and r.json()["delai_jours"] == 12
    assert http.patch(f"{API}/catalogue/{pid}", headers=auth["admin"], json={"nom": "Robe"}).status_code == 409
    assert http.get(f"{API}/catalogue/9999", headers=auth["admin"]).status_code == 404
