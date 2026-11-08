from tests.conftest import MOT_DE_PASSE

API = "/api/v1"


def login(http, email, mdp=MOT_DE_PASSE):
    return http.post(f"{API}/auth/login", data={"username": email, "password": mdp})


def test_login_ok_renvoie_un_jeton(http, utilisateurs):
    r = login(http, "accueil@atelier.sn")
    assert r.status_code == 200
    corps = r.json()
    assert corps["token_type"] == "bearer" and corps["expires_in"] > 0
    me = http.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {corps['access_token']}"})
    assert me.status_code == 200 and me.json()["role"] == "accueil"


def test_profil_sans_donnee_sensible(http, auth):
    corps = http.get(f"{API}/auth/me", headers=auth["admin"]).json()
    assert "mot_de_passe_hash" not in corps and "mot_de_passe" not in corps


def test_meme_message_email_inconnu_ou_mauvais_mot_de_passe(http, utilisateurs):  # RG23
    a = login(http, "inconnu@atelier.sn")
    b = login(http, "accueil@atelier.sn", "mauvais-mot-de-passe")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_sans_jeton_ou_jeton_invalide_401(http, utilisateurs):
    assert http.get(f"{API}/clients").status_code == 401
    assert http.get(f"{API}/clients", headers={"Authorization": "Bearer nimporte.quoi"}).status_code == 401


def test_compte_desactive_refuse_meme_avec_jeton_valide(http, auth, utilisateurs):  # RG22
    uid = utilisateurs["tailleur"].id
    assert http.patch(f"{API}/utilisateurs/{uid}", headers=auth["admin"], json={"actif": False}).status_code == 200
    assert http.get(f"{API}/clients", headers=auth["tailleur"]).status_code == 401
    assert login(http, "tailleur@atelier.sn").status_code == 401


def test_creation_utilisateur_et_mot_de_passe_jamais_renvoye(http, auth):
    corps = {"email": "Nouveau@Atelier.sn", "nom_complet": "Nouveau", "mot_de_passe": "unmotdepasse", "role": "accueil"}
    r = http.post(f"{API}/utilisateurs", headers=auth["admin"], json=corps)
    assert r.status_code == 201
    assert r.json()["email"] == "nouveau@atelier.sn"
    assert "mot_de_passe" not in r.json() and "mot_de_passe_hash" not in r.json()
    assert login(http, "nouveau@atelier.sn", "unmotdepasse").status_code == 200
    assert http.post(f"{API}/utilisateurs", headers=auth["admin"], json=corps).status_code == 409


def test_mot_de_passe_trop_court_422(http, auth):  # RG21
    r = http.post(f"{API}/utilisateurs", headers=auth["admin"],
                  json={"email": "a@b.sn", "nom_complet": "A", "mot_de_passe": "court", "role": "accueil"})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_admin_ne_peut_pas_se_desactiver_ni_se_retrograder(http, auth, utilisateurs):  # RG24
    uid = utilisateurs["admin"].id
    assert http.patch(f"{API}/utilisateurs/{uid}", headers=auth["admin"], json={"actif": False}).status_code == 409
    assert http.patch(f"{API}/utilisateurs/{uid}", headers=auth["admin"], json={"role": "accueil"}).status_code == 409
    # Il peut en revanche modifier un AUTRE admin
    autre = utilisateurs["admin2"].id
    assert http.patch(f"{API}/utilisateurs/{autre}", headers=auth["admin"], json={"actif": False}).status_code == 200


def test_changement_de_mot_de_passe(http, auth, utilisateurs):
    uid = utilisateurs["accueil"].id
    http.patch(f"{API}/utilisateurs/{uid}", headers=auth["admin"], json={"mot_de_passe": "nouveaumdp123"})
    assert login(http, "accueil@atelier.sn").status_code == 401
    assert login(http, "accueil@atelier.sn", "nouveaumdp123").status_code == 200


def test_utilisateur_inconnu_404(http, auth):
    assert http.get(f"{API}/utilisateurs/9999", headers=auth["admin"]).status_code == 404


def test_health(http):
    assert http.get("/health").json() == {"status": "ok"}
