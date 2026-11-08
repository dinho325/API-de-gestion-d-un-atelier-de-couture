from datetime import date, timedelta

from app.models import Commande

API = "/api/v1"


def statut(http, auth, cid, cible, role="tailleur", commentaire=None):
    corps = {"statut": cible, **({"commentaire": commentaire} if commentaire else {})}
    return http.post(f"{API}/commandes/{cid}/statut", headers=auth[role], json=corps)


def test_creation_numero_montants_et_date_prevue(http, auth, client_fatou, catalogue, utilisateurs):  # RG5-8
    corps = {
        "client_id": client_fatou["id"], "remise": 5000,
        "lignes": [
            {"type_vetement_id": catalogue["Boubou"], "quantite": 2},                       # 70 000
            {"type_vetement_id": catalogue["Pantalon"], "quantite": 1, "prix_unitaire": 10000},  # prix négocié
        ],
    }
    r = http.post(f"{API}/commandes", headers=auth["accueil"], json=corps)
    assert r.status_code == 201
    c = r.json()
    assert c["numero"] == f"CMD-{date.today().year}-{c['id']:05d}"
    assert c["statut"] == "en_attente"
    assert c["montant_total"] == 75000 and c["montant_paye"] == 0 and c["solde"] == 75000
    assert [l["prix_unitaire"] for l in c["lignes"]] == [35000, 10000]
    assert c["lignes"][0]["sous_total"] == 70000 and c["lignes"][0]["type_vetement_nom"] == "Boubou"
    # Date prévue = date de commande + plus long délai (Boubou : 10 jours)
    assert c["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert c["cree_par_id"] == utilisateurs["accueil"].id and c["en_retard"] is False


def test_le_client_ne_peut_pas_imposer_les_montants(http, auth, client_fatou, catalogue):
    corps = {"client_id": client_fatou["id"], "montant_total": 1, "statut": "livree", "numero": "X",
             "lignes": [{"type_vetement_id": catalogue["Boubou"]}]}
    c = http.post(f"{API}/commandes", headers=auth["accueil"], json=corps).json()
    assert c["montant_total"] == 35000 and c["statut"] == "en_attente" and c["numero"].startswith("CMD-")


def test_remise_superieure_aux_prestations_422(http, auth, client_fatou, catalogue):  # RG7
    r = http.post(f"{API}/commandes", headers=auth["accueil"], json={
        "client_id": client_fatou["id"], "remise": 12001,
        "lignes": [{"type_vetement_id": catalogue["Pantalon"]}]})
    assert r.status_code == 422


def test_prestation_inactive_422_et_inconnue_404(http, auth, client_fatou, catalogue):  # RG6
    http.patch(f"{API}/catalogue/{catalogue['Robe']}", headers=auth["admin"], json={"actif": False})
    corps = {"client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Robe"]}]}
    assert http.post(f"{API}/commandes", headers=auth["accueil"], json=corps).status_code == 422
    corps["lignes"] = [{"type_vetement_id": 9999}]
    assert http.post(f"{API}/commandes", headers=auth["accueil"], json=corps).status_code == 404


def test_date_prevue_avant_date_commande_422(http, auth, client_fatou, catalogue):  # RG8
    hier = (date.today() - timedelta(days=1)).isoformat()
    r = http.post(f"{API}/commandes", headers=auth["accueil"], json={
        "client_id": client_fatou["id"], "date_livraison_prevue": hier,
        "lignes": [{"type_vetement_id": catalogue["Robe"]}]})
    assert r.status_code == 422


def test_commande_sans_ligne_422(http, auth, client_fatou):
    assert http.post(f"{API}/commandes", headers=auth["accueil"],
                     json={"client_id": client_fatou["id"], "lignes": []}).status_code == 422


def test_mesures_dun_autre_client_422(http, auth, client_fatou, catalogue):  # RG9
    autre = http.post(f"{API}/clients", headers=auth["accueil"],
                      json={"nom": "Fall", "prenom": "Omar", "telephone": "700000009"}).json()
    mesure = http.post(f"{API}/clients/{autre['id']}/mesures", headers=auth["tailleur"], json={"tour_cou": 40}).json()
    r = http.post(f"{API}/commandes", headers=auth["accueil"], json={
        "client_id": client_fatou["id"], "mesure_id": mesure["id"],
        "lignes": [{"type_vetement_id": catalogue["Robe"]}]})
    assert r.status_code == 422


def test_historique_cree_avec_la_commande(http, auth, faire_commande):  # RG15
    c = faire_commande()
    h = http.get(f"{API}/commandes/{c['id']}/historique", headers=auth["tailleur"]).json()
    assert len(h) == 1 and h[0]["ancien_statut"] is None and h[0]["nouveau_statut"] == "en_attente"


def test_liste_filtres_et_champs_calcules(http, auth, db, faire_commande, client_fatou):
    a = faire_commande(lignes=[("Pantalon", 1)])
    b = faire_commande(lignes=[("Boubou", 1)])
    statut(http, auth, b["id"], "en_coupe")
    liste = http.get(f"{API}/commandes", headers=auth["tailleur"]).json()
    assert [c["id"] for c in liste["items"]] == [b["id"], a["id"]]
    premier = liste["items"][0]
    assert premier["client_nom"] == "Fatou Diop" and "solde" in premier and "en_retard" in premier
    assert http.get(f"{API}/commandes?statut=en_coupe", headers=auth["tailleur"]).json()["total"] == 1
    assert http.get(f"{API}/commandes?client_id={client_fatou['id']}", headers=auth["tailleur"]).json()["total"] == 2
    assert http.get(f"{API}/commandes?numero={a['numero']}", headers=auth["tailleur"]).json()["total"] == 1
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert http.get(f"{API}/commandes?date_min={demain}", headers=auth["tailleur"]).json()["total"] == 0


def test_commande_en_retard(http, auth, db, faire_commande):  # RG11
    c = faire_commande()
    ligne = db.get(Commande, c["id"])
    ligne.date_livraison_prevue = date.today() - timedelta(days=3)
    db.commit()
    assert http.get(f"{API}/commandes/{c['id']}", headers=auth["tailleur"]).json()["en_retard"] is True
    assert http.get(f"{API}/commandes?en_retard=true", headers=auth["tailleur"]).json()["total"] == 1
    assert http.get(f"{API}/commandes?en_retard=false", headers=auth["tailleur"]).json()["total"] == 0
    statut(http, auth, c["id"], "annulee", role="accueil")   # annulée : plus « en retard »
    assert http.get(f"{API}/commandes/{c['id']}", headers=auth["tailleur"]).json()["en_retard"] is False


def test_modification_recalcule_les_montants(http, auth, faire_commande):  # RG7
    c = faire_commande(lignes=[("Boubou", 2)])
    r = http.patch(f"{API}/commandes/{c['id']}", headers=auth["accueil"], json={"remise": 10000, "notes": "Urgent"})
    assert r.status_code == 200
    assert r.json()["montant_total"] == 60000 and r.json()["notes"] == "Urgent"
    assert http.patch(f"{API}/commandes/{c['id']}", headers=auth["accueil"], json={"remise": 70001}).status_code == 422


def test_le_total_ne_peut_pas_passer_sous_le_montant_paye_409(http, auth, faire_commande):  # RG7
    c = faire_commande(lignes=[("Boubou", 2)])  # 70 000
    http.post(f"{API}/commandes/{c['id']}/paiements", headers=auth["accueil"], json={"montant": 50000, "mode": "wave"})
    r = http.patch(f"{API}/commandes/{c['id']}", headers=auth["accueil"], json={"remise": 30000})  # total 40 000 < 50 000
    assert r.status_code == 409
    assert http.get(f"{API}/commandes/{c['id']}", headers=auth["accueil"]).json()["remise"] == 0


def test_lignes_ajout_et_retrait_en_attente(http, auth, catalogue, faire_commande):  # RG10
    c = faire_commande(lignes=[("Boubou", 1)])
    r = http.post(f"{API}/commandes/{c['id']}/lignes", headers=auth["accueil"],
                  json={"type_vetement_id": catalogue["Chemise"], "quantite": 2})
    assert r.status_code == 201 and r.json()["montant_total"] == 65000 and len(r.json()["lignes"]) == 2
    ligne_id = r.json()["lignes"][1]["id"]
    r = http.delete(f"{API}/commandes/{c['id']}/lignes/{ligne_id}", headers=auth["accueil"])
    assert r.status_code == 200 and r.json()["montant_total"] == 35000
    assert http.delete(f"{API}/commandes/{c['id']}/lignes/{ligne_id}", headers=auth["accueil"]).status_code == 404


def test_une_commande_garde_au_moins_une_ligne_409(http, auth, faire_commande):  # RG10
    c = faire_commande(lignes=[("Boubou", 1)])
    r = http.delete(f"{API}/commandes/{c['id']}/lignes/{c['lignes'][0]['id']}", headers=auth["accueil"])
    assert r.status_code == 409


def test_lignes_verrouillees_hors_en_attente_409(http, auth, catalogue, faire_commande):  # RG10
    c = faire_commande(lignes=[("Boubou", 1), ("Pantalon", 1)])
    statut(http, auth, c["id"], "en_coupe")
    assert http.post(f"{API}/commandes/{c['id']}/lignes", headers=auth["accueil"],
                     json={"type_vetement_id": catalogue["Robe"]}).status_code == 409
    assert http.delete(f"{API}/commandes/{c['id']}/lignes/{c['lignes'][1]['id']}", headers=auth["accueil"]).status_code == 409


# --------------------------------------------------------------- workflow
def test_workflow_complet_avec_aller_retour_essayage_retouches(http, auth, faire_commande, avancer):
    c = faire_commande()
    avancer(c["id"], "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee")
    h = http.get(f"{API}/commandes/{c['id']}/historique", headers=auth["tailleur"]).json()
    assert [x["nouveau_statut"] for x in h] == [
        "en_attente", "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]
    assert h[-1]["ancien_statut"] == "essayage" and h[-1]["utilisateur_id"] is not None


def test_transition_interdite_409_avec_statuts_possibles(http, auth, faire_commande):
    c = faire_commande()
    r = statut(http, auth, c["id"], "terminee", role="accueil")
    assert r.status_code == 409
    assert r.json()["detail"] == "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"


def test_meme_statut_refuse_409(http, auth, faire_commande):  # RG13
    c = faire_commande()
    assert statut(http, auth, c["id"], "en_attente").status_code == 409


def test_livree_impossible_par_la_route_de_statut_409(http, auth, faire_commande, avancer):  # RG13
    c = faire_commande()
    avancer(c["id"], "en_coupe", "en_couture", "terminee")
    r = statut(http, auth, c["id"], "livree", role="accueil")
    assert r.status_code == 409 and "livraison" in r.json()["detail"]


def test_statut_inconnu_422(http, auth, faire_commande):
    c = faire_commande()
    assert statut(http, auth, c["id"], "n_importe_quoi").status_code == 422


def test_le_tailleur_ne_peut_pas_annuler_403(http, auth, faire_commande):  # RG14
    c = faire_commande()
    assert statut(http, auth, c["id"], "annulee", role="tailleur").status_code == 403
    assert statut(http, auth, c["id"], "annulee", role="accueil").status_code == 200


def test_annuler_une_commande_avec_acompte_exige_un_commentaire_422(http, auth, faire_commande):  # RG14
    c = faire_commande()
    http.post(f"{API}/commandes/{c['id']}/paiements", headers=auth["accueil"], json={"montant": 5000, "mode": "especes"})
    assert statut(http, auth, c["id"], "annulee", role="accueil").status_code == 422
    assert statut(http, auth, c["id"], "annulee", role="accueil", commentaire="   ").status_code == 422
    r = statut(http, auth, c["id"], "annulee", role="accueil", commentaire="Acompte remboursé en espèces")
    assert r.status_code == 200
    h = http.get(f"{API}/commandes/{c['id']}/historique", headers=auth["accueil"]).json()
    assert h[-1]["commentaire"] == "Acompte remboursé en espèces"


def test_commande_annulee_ou_livree_non_modifiable_409(http, auth, catalogue, faire_commande):  # RG12
    c = faire_commande()
    statut(http, auth, c["id"], "annulee", role="accueil")
    assert http.patch(f"{API}/commandes/{c['id']}", headers=auth["accueil"], json={"notes": "x"}).status_code == 409
    assert http.post(f"{API}/commandes/{c['id']}/lignes", headers=auth["accueil"],
                     json={"type_vetement_id": catalogue["Robe"]}).status_code == 409
    assert statut(http, auth, c["id"], "en_coupe").status_code == 409   # statut final


def test_commande_inconnue_404(http, auth):
    assert http.get(f"{API}/commandes/999", headers=auth["accueil"]).status_code == 404
    assert statut(http, auth, 999, "en_coupe").status_code == 404
