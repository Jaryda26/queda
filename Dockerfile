# API de Queda (FastAPI) para Render / Railway / cualquier servidor con Docker.
# La app web de Streamlit NO usa este archivo (Streamlit Cloud lo ignora).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements_api.txt .
RUN pip install -r requirements_api.txt

# Solo lo que la API necesita (ver .dockerignore)
COPY . .

# Render/Railway inyectan $PORT; en local cae a 8000.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
