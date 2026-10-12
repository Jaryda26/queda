import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt, JWTError

# Cargar el .env AQUÍ: este módulo se importa antes que db.py,
# y sin esto API_JWT_SECRET aún no existe en el entorno.
load_dotenv()

# El secreto YA NO va en el código. Defínelo en tu .env:
#   API_JWT_SECRET=<cadena larga aleatoria>
# Genera una con:  python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY = os.getenv("API_JWT_SECRET")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Falta API_JWT_SECRET (mínimo 32 caracteres) en el .env"
    )

ALGORITHM = "HS256"
# Móvil: sesión larga (como la web, 30 días).
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30


def crear_token(data: dict):

    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def validar_token(token: str):

    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
