"""Configuration lue dans les variables d'environnement (ou le fichier .env).

Aucune valeur secrète n'est écrite dans le code : si SECRET_KEY ou
DATABASE_URL manquent, l'application refuse de démarrer.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Utilisés uniquement par `python -m app.seed`
    admin_email: str | None = None
    admin_password: str | None = None
    admin_nom: str = "Administrateur"
    seed_demo_users: bool = False
    demo_password: str | None = None


settings = Settings()
