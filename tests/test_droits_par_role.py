"""Matrice des droits : un test par rôle (401 sans jeton, 403 si rôle insuffisant)."""
import pytest

API = "/api/v1"


def appel(http, methode, url, headers=None, json=None):
    return http.request(methode, f"{API}{url}", headers=headers, json=json)


def test_toute_route_protegee_exige_un_jeton(http):
    for methode, url in [("GET", "/clients"), ("GET", "/commandes"), ("GET", "/catalogue"),
                         ("GET", "/livraisons"), ("GET", "/statistiques/impayes"), ("GET", "/utilisateurs")]:
        assert appel(http, methode, url).status_code == 401


def test_accueil_ne_peut_pas_prendre_de_mesures(http, auth, client_fatou):  # demo, étape 2
    r = appel(http, "POST", f"/clients/{client_fatou['id']}/mesures", auth["accueil"], {"tour_cou": 40})
    assert r.status_code == 403


def test_tailleur_ne_cree_ni_commande_ni_paiement(http, auth, client_fatou, catalogue, faire_commande):
    corps = {"client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Robe"]}]}
    assert appel(http, "POST", "/commandes", auth["tailleur"], corps).status_code == 403
    c = faire_commande()
    assert appel(http, "POST", f"/commandes/{c['id']}/paiements", auth["tailleur"],
                 {"montant": 1000, "mode": "wave"}).status_code == 403
    assert appel(http, "PUT", f"/commandes/{c['id']}/livraison", auth["tailleur"],
                 {"mode": "retrait_atelier", "date_prevue": "2030-01-01"}).status_code == 403
    assert appel(http, "POST", f"/commandes/{c['id']}/livraison/confirmer", auth["tailleur"]).status_code == 403
    assert appel(http, "PATCH", f"/commandes/{c['id']}", auth["tailleur"], {"notes": "x"}).status_code == 403


@pytest.mark.parametrize("role", ["accueil", "tailleur"])
def test_routes_reservees_a_ladmin(http, auth, client_fatou, faire_commande, role):
    c = faire_commande()
    assert appel(http, "GET", "/utilisateurs", auth[role]).status_code == 403
    assert appel(http, "POST", "/utilisateurs", auth[role], {"email": "a@b.sn", "nom_complet": "A",
                                                             "mot_de_passe": "12345678", "role": "admin"}).status_code == 403
    assert appel(http, "POST", "/catalogue", auth[role], {"nom": "X", "prix_base": 1, "delai_jours": 1}).status_code == 403
    assert appel(http, "PATCH", "/catalogue/1", auth[role], {"prix_base": 1}).status_code == 403
    assert appel(http, "DELETE", f"/clients/{client_fatou['id']}", auth[role]).status_code == 403
    assert appel(http, "DELETE", "/paiements/1", auth[role]).status_code == 403
    for chemin in ("tableau-de-bord", "chiffre-affaires", "types-vetement", "top-clients", "impayes"):
        assert appel(http, "GET", f"/statistiques/{chemin}", auth[role]).status_code == 403   # demo, étape 9


def test_tout_utilisateur_connecte_peut_consulter(http, auth, client_fatou, faire_commande):
    c = faire_commande()
    for role in ("accueil", "tailleur", "admin"):
        for url in ("/clients", f"/clients/{client_fatou['id']}", "/commandes", f"/commandes/{c['id']}",
                    "/catalogue", "/livraisons", f"/commandes/{c['id']}/historique",
                    f"/commandes/{c['id']}/paiements", f"/clients/{client_fatou['id']}/mesures"):
            assert appel(http, "GET", url, auth[role]).status_code == 200, (role, url)


def test_ladmin_peut_tout_faire(http, auth, client_fatou, catalogue):
    assert appel(http, "POST", f"/clients/{client_fatou['id']}/mesures", auth["admin"], {"tour_cou": 40}).status_code == 201
    r = appel(http, "POST", "/commandes", auth["admin"], {"client_id": client_fatou["id"],
              "lignes": [{"type_vetement_id": catalogue["Robe"]}]})
    assert r.status_code == 201
    assert appel(http, "GET", "/statistiques/tableau-de-bord", auth["admin"]).status_code == 200
