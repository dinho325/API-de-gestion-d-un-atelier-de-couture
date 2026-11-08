"""Tests des fonctions métier SANS passer par HTTP (c'est l'intérêt de la couche services)."""
import pytest

from app.enums import StatutCommande as S
from app.models import Commande, LigneCommande, Paiement
from app.services.commandes import TRANSITIONS, _decrire_statuts, recalculer_montants
from app.utils import normaliser_telephone


@pytest.mark.parametrize("saisie, attendu", [
    ("77 123 45 67", "771234567"),
    ("771234567", "771234567"),
    ("(77) 123-45.67", "771234567"),
    ("+221 77 123 45 67", "+221771234567"),
])
def test_normalisation_telephone(saisie, attendu):  # RG1
    assert normaliser_telephone(saisie) == attendu


@pytest.mark.parametrize("saisie", ["12345", "abc", "77 12 ab 67", "++221771234567", "1" * 21, ""])
def test_telephone_invalide(saisie):
    with pytest.raises(ValueError):
        normaliser_telephone(saisie)


def test_calcul_des_montants():  # RG7
    commande = Commande(remise=5000)
    commande.lignes = [
        LigneCommande(quantite=2, prix_unitaire=35000),
        LigneCommande(quantite=1, prix_unitaire=10000),
    ]
    commande.paiements = [Paiement(montant=20000), Paiement(montant=10000)]
    recalculer_montants(commande)
    assert commande.montant_total == 75000  # 70000 + 10000 - 5000
    assert commande.montant_paye == 30000
    assert commande.solde == 45000


def test_table_des_transitions():
    assert TRANSITIONS[S.en_attente] == {S.en_coupe, S.annulee}
    assert TRANSITIONS[S.retouches] == {S.essayage, S.terminee, S.annulee}
    assert TRANSITIONS[S.terminee] == {S.livree}
    assert TRANSITIONS[S.livree] == set() and TRANSITIONS[S.annulee] == set()


def test_message_statuts_possibles():
    assert _decrire_statuts({S.en_coupe, S.annulee}) == "annulee, en_coupe"
    assert _decrire_statuts(set()) == "aucun"
    assert "confirmation de livraison" in _decrire_statuts({S.livree})
