from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import tout_utilisateur
from app.models import Utilisateur
from app.schemas.utilisateur import Jeton, UtilisateurLecture
from app.security import creer_jeton
from app.services import utilisateurs as service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def connexion(formulaire: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Formulaire OAuth2 : `username` = e-mail, `password` = mot de passe."""
    utilisateur = service.authentifier(db, formulaire.username, formulaire.password)
    jeton, expires_in = creer_jeton(utilisateur.id)
    return Jeton(access_token=jeton, expires_in=expires_in)


@router.get("/me", response_model=UtilisateurLecture)
def profil(utilisateur: Utilisateur = Depends(tout_utilisateur)):
    return utilisateur
