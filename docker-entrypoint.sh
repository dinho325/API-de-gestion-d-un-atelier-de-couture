#!/bin/sh
# Au démarrage du conteneur : migrations -> données initiales -> serveur
set -e
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
