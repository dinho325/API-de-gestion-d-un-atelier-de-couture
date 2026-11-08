"""Point d'entrée : assemble l'application FastAPI."""
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ErreurMetier
from app.routers import (
    auth, catalogue, clients, commandes, livraisons, mesures, paiements,
    statistiques, utilisateurs,
)

app = FastAPI(
    title="Atelier de couture – API de gestion",
    description="API REST de gestion des clients, mesures, commandes, paiements et livraisons.",
    version="1.0.0",
)

api_v1 = APIRouter(prefix="/api/v1")
for module in (
    auth, utilisateurs, clients, catalogue, mesures, commandes, paiements,
    livraisons, statistiques,
):
    api_v1.include_router(module.router)
app.include_router(api_v1)


# erreurs
@app.exception_handler(ErreurMetier)
async def gerer_erreur_metier(_: Request, erreur: ErreurMetier):
    """Toutes les erreurs métier ont la forme {"detail": "message"}."""
    entetes = {"WWW-Authenticate": "Bearer"} if erreur.status_code == 401 else None
    return JSONResponse(status_code=erreur.status_code, content={"detail": erreur.message}, headers=entetes)


def _traduire(erreur: dict) -> str:
    """Rend un message d'erreur Pydantic lisible, en français."""
    type_, ctx = erreur.get("type", ""), erreur.get("ctx", {})
    messages = {
        "missing": "champ obligatoire",
        "string_too_short": f"trop court (minimum {ctx.get('min_length')} caractères)",
        "string_too_long": f"trop long (maximum {ctx.get('max_length')} caractères)",
        "too_short": f"au moins {ctx.get('min_length')} élément(s) requis",
        "greater_than": f"doit être strictement supérieur à {ctx.get('gt')}",
        "greater_than_equal": f"doit être supérieur ou égal à {ctx.get('ge')}",
        "less_than_equal": f"doit être inférieur ou égal à {ctx.get('le')}",
        "less_than": f"doit être strictement inférieur à {ctx.get('lt')}",
        "int_parsing": "doit être un nombre entier",
        "float_parsing": "doit être un nombre",
        "bool_parsing": "doit être vrai ou faux",
        "date_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
        "date_from_datetime_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
        "enum": f"valeur invalide (valeurs possibles : {ctx.get('expected')})",
        "json_invalid": "corps JSON invalide",
        "string_type": "doit être un texte",
    }
    if type_ in messages:
        return messages[type_]
    if type_ == "value_error":
        return erreur["msg"].removeprefix("Value error, ")
    return erreur["msg"]


@app.exception_handler(RequestValidationError)
async def gerer_validation(_: Request, erreur: RequestValidationError):
    """422 : liste claire des champs invalides, au format {"detail": "..."}."""
    morceaux = []
    for e in erreur.errors():
        champ = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path"))
        message = _traduire(e)
        morceaux.append(f"{champ} : {message}" if champ else message)
    return JSONResponse(status_code=422, content={"detail": "Données invalides — " + " ; ".join(morceaux)})


# santé
@app.get("/health", tags=["Santé"])
def sante(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Base de données indisponible."})
    return {"status": "ok"}
