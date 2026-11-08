"""Petites fonctions utilitaires sans dépendance au reste de l'application."""
import re
from datetime import date, datetime, timezone

_SEPARATEURS = re.compile(r"[\s.\-()]")
_TELEPHONE_VALIDE = re.compile(r"^\+?\d{6,20}$")


def aujourdhui() -> date:
    """Date du jour. Centralisée ici pour pouvoir la « figer » dans les tests."""
    return date.today()


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


def normaliser_telephone(valeur: str) -> str:
    """RG1 : supprime espaces, points, tirets et parenthèses, puis valide.

    « 77 123 45 67 » et « 771234567 » donnent la même valeur.
    Forme valide : 6 à 20 chiffres, « + » initial facultatif.
    Lève ValueError si le numéro est invalide.
    """
    nettoye = _SEPARATEURS.sub("", valeur)
    if not _TELEPHONE_VALIDE.match(nettoye):
        raise ValueError(
            "Numéro de téléphone invalide : 6 à 20 chiffres attendus, "
            "avec un « + » initial facultatif."
        )
    return nettoye
