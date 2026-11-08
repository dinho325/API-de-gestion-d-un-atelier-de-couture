"""Rejoue l'annexe A de l'énoncé de bout en bout."""
from scripts.scenario_demo import jouer
from tests.conftest import MOT_DE_PASSE


def test_scenario_de_demonstration(http, catalogue, utilisateurs):
    comptes = {role: (f"{role}@atelier.sn", MOT_DE_PASSE) for role in ("admin", "accueil", "tailleur")}
    jouer(http, comptes, afficher=lambda _: None)
