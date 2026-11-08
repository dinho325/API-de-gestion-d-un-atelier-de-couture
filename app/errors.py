"""Erreurs métier : levées par les services, converties en réponse HTTP
{"detail": "..."} par un gestionnaire global (voir app/main.py).

Ainsi les services ne dépendent pas de FastAPI et restent testables seuls.
"""


class ErreurMetier(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NonAuthentifie(ErreurMetier):
    status_code = 401


class Interdit(ErreurMetier):
    status_code = 403


class NonTrouve(ErreurMetier):
    status_code = 404


class Conflit(ErreurMetier):
    status_code = 409


class DonneeInvalide(ErreurMetier):
    status_code = 422
