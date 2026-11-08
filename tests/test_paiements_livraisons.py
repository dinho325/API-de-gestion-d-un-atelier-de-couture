from datetime import date, timedelta

API = "/api/v1"


def payer(http, auth, cid, montant, mode="wave", **extra):
    return http.post(f"{API}/commandes/{cid}/paiements", headers=auth["accueil"],
                     json={"montant": montant, "mode": mode, **extra})


def detail(http, auth, cid):
    return http.get(f"{API}/commandes/{cid}", headers=auth["accueil"]).json()


# ------------------------------------------------------------------ paiements
def test_acompte_puis_solde(http, auth, faire_commande):
    c = faire_commande(lignes=[("Boubou", 2)])     # 70 000
    r = payer(http, auth, c["id"], 20000, reference="WV123")
    assert r.status_code == 201 and r.json()["reference"] == "WV123"
    d = detail(http, auth, c["id"])
    assert d["montant_paye"] == 20000 and d["solde"] == 50000 and len(d["paiements"]) == 1
    payer(http, auth, c["id"], 50000, mode="especes")
    assert detail(http, auth, c["id"])["solde"] == 0
    liste = http.get(f"{API}/commandes/{c['id']}/paiements", headers=auth["tailleur"]).json()
    assert [p["montant"] for p in liste] == [20000, 50000]


def test_paiement_superieur_au_solde_409(http, auth, faire_commande):  # RG16
    c = faire_commande(lignes=[("Pantalon", 1)])
    assert payer(http, auth, c["id"], 12001).status_code == 409


def test_paiement_negatif_ou_nul_422(http, auth, faire_commande):  # RG16
    c = faire_commande()
    assert payer(http, auth, c["id"], 0).status_code == 422
    assert payer(http, auth, c["id"], -100).status_code == 422
    assert payer(http, auth, c["id"], 1000, mode="bitcoin").status_code == 422


def test_paiement_date_future_422(http, auth, faire_commande):  # RG16
    c = faire_commande()
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert payer(http, auth, c["id"], 1000, date_paiement=demain).status_code == 422
    assert payer(http, auth, c["id"], 1000, date_paiement=date.today().isoformat()).status_code == 201


def test_paiement_sur_commande_annulee_409(http, auth, faire_commande):  # RG16
    c = faire_commande()
    http.post(f"{API}/commandes/{c['id']}/statut", headers=auth["accueil"], json={"statut": "annulee"})
    assert payer(http, auth, c["id"], 1000).status_code == 409


def test_annulation_de_paiement_recalcule_le_solde(http, auth, faire_commande):  # RG17
    c = faire_commande(lignes=[("Boubou", 1)])
    p = payer(http, auth, c["id"], 15000).json()
    assert detail(http, auth, c["id"])["solde"] == 20000
    assert http.delete(f"{API}/paiements/{p['id']}", headers=auth["admin"]).status_code == 204
    d = detail(http, auth, c["id"])
    assert d["montant_paye"] == 0 and d["solde"] == 35000 and d["paiements"] == []
    assert http.delete(f"{API}/paiements/{p['id']}", headers=auth["admin"]).status_code == 404


# ----------------------------------------------------------------- livraisons
def terminer(faire_commande, avancer, **kw):
    c = faire_commande(**kw)
    avancer(c["id"], "en_coupe", "en_couture", "terminee")
    return c


def test_livraison_a_domicile_exige_une_adresse_422(http, auth, faire_commande):  # RG18
    c = faire_commande()
    url = f"{API}/commandes/{c['id']}/livraison"
    corps = {"mode": "domicile", "date_prevue": (date.today() + timedelta(days=12)).isoformat()}
    assert http.put(url, headers=auth["accueil"], json=corps).status_code == 422
    assert http.put(url, headers=auth["accueil"], json={**corps, "adresse": "Sacré-Cœur 3"}).status_code == 200


def test_planification_met_a_jour_la_date_et_replanifier_ne_duplique_pas(http, auth, faire_commande):  # RG18
    c = faire_commande()
    url = f"{API}/commandes/{c['id']}/livraison"
    assert http.get(url, headers=auth["accueil"]).status_code == 404
    d1 = (date.today() + timedelta(days=12)).isoformat()
    d2 = (date.today() + timedelta(days=15)).isoformat()
    a = http.put(url, headers=auth["accueil"], json={"mode": "retrait_atelier", "date_prevue": d1}).json()
    assert detail(http, auth, c["id"])["date_livraison_prevue"] == d1
    b = http.put(url, headers=auth["accueil"], json={"mode": "domicile", "adresse": "Plateau", "livreur": "Modou",
                                                      "date_prevue": d2}).json()
    assert a["id"] == b["id"] and b["mode"] == "domicile" and b["livreur"] == "Modou"
    assert detail(http, auth, c["id"])["date_livraison_prevue"] == d2
    assert len(http.get(f"{API}/livraisons", headers=auth["accueil"]).json()) == 1


def test_confirmation_exige_une_commande_terminee_409(http, auth, faire_commande):  # RG19
    c = faire_commande()
    assert http.post(f"{API}/commandes/{c['id']}/livraison/confirmer", headers=auth["accueil"]).status_code == 409


def test_confirmation_refusee_si_solde_impaye_409(http, auth, faire_commande, avancer):  # RG19
    c = terminer(faire_commande, avancer, lignes=[("Boubou", 1)])
    payer(http, auth, c["id"], 10000)
    r = http.post(f"{API}/commandes/{c['id']}/livraison/confirmer", headers=auth["accueil"])
    assert r.status_code == 409 and "25000" in r.json()["detail"]


def test_confirmation_avec_solde_impaye_autorise_garde_la_dette_et_la_mention(http, auth, faire_commande, avancer):  # RG19
    c = terminer(faire_commande, avancer, lignes=[("Boubou", 1)])
    payer(http, auth, c["id"], 10000)
    r = http.post(f"{API}/commandes/{c['id']}/livraison/confirmer", headers=auth["accueil"],
                  json={"autoriser_solde_impaye": True})
    assert r.status_code == 200 and r.json()["statut"] == "livree" and r.json()["solde"] == 25000
    dernier = http.get(f"{API}/commandes/{c['id']}/historique", headers=auth["accueil"]).json()[-1]
    assert "impayé" in dernier["commentaire"] and dernier["nouveau_statut"] == "livree"


def test_confirmation_cree_un_retrait_atelier_et_solde_la_commande(http, auth, faire_commande, avancer):  # RG20
    c = terminer(faire_commande, avancer, lignes=[("Pantalon", 1)])
    payer(http, auth, c["id"], 12000)
    r = http.post(f"{API}/commandes/{c['id']}/livraison/confirmer", headers=auth["accueil"])
    assert r.status_code == 200
    d = r.json()
    aujourdhui = date.today().isoformat()
    assert d["statut"] == "livree" and d["solde"] == 0 and d["date_livraison_reelle"] == aujourdhui
    assert d["livraison"]["mode"] == "retrait_atelier" and d["livraison"]["statut"] == "livree"
    assert d["livraison"]["date_effective"] == aujourdhui
    # Une fois livrée : plus modifiable
    assert http.put(f"{API}/commandes/{c['id']}/livraison", headers=auth["accueil"],
                    json={"mode": "retrait_atelier", "date_prevue": aujourdhui}).status_code == 409


def test_confirmation_utilise_la_livraison_planifiee(http, auth, faire_commande, avancer):  # RG20
    c = terminer(faire_commande, avancer, lignes=[("Pantalon", 1)])
    payer(http, auth, c["id"], 12000)
    http.put(f"{API}/commandes/{c['id']}/livraison", headers=auth["accueil"], json={
        "mode": "domicile", "adresse": "Yoff", "date_prevue": (date.today() + timedelta(days=2)).isoformat()})
    d = http.post(f"{API}/commandes/{c['id']}/livraison/confirmer", headers=auth["accueil"],
                  json={"date_effective": date.today().isoformat()}).json()
    assert d["livraison"]["mode"] == "domicile" and d["livraison"]["statut"] == "livree"
    assert len(http.get(f"{API}/livraisons", headers=auth["accueil"]).json()) == 1


def test_tournee_triee_filtrable_et_enrichie(http, auth, faire_commande):
    c1, c2 = faire_commande(lignes=[("Boubou", 1)]), faire_commande(lignes=[("Pantalon", 1)])
    tard, tot = (date.today() + timedelta(days=9)), (date.today() + timedelta(days=5))
    http.put(f"{API}/commandes/{c1['id']}/livraison", headers=auth["accueil"],
             json={"mode": "retrait_atelier", "date_prevue": tard.isoformat()})
    http.put(f"{API}/commandes/{c2['id']}/livraison", headers=auth["accueil"],
             json={"mode": "retrait_atelier", "date_prevue": tot.isoformat()})
    tournee = http.get(f"{API}/livraisons", headers=auth["tailleur"]).json()
    assert [t["numero_commande"] for t in tournee] == [c2["numero"], c1["numero"]]
    assert tournee[0]["client_nom"] == "Fatou Diop" and tournee[0]["client_telephone"] == "771234567"
    assert tournee[0]["solde_commande"] == 12000
    assert len(http.get(f"{API}/livraisons?date_min={tard.isoformat()}", headers=auth["tailleur"]).json()) == 1
    assert http.get(f"{API}/livraisons?statut=livree", headers=auth["tailleur"]).json() == []
