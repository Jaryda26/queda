# Voz en el celular — cambios WEB + API

Copia TODO este zip sobre tu proyecto (respeta carpetas) y súbelo a Streamlit con git.

## Archivos
- api/            -> nuevo: voz_service.py, voz.py (POST /voz/comando) + main.py, user_service.py, __init__.py
- services/estado_voz.py     NUEVO (en la web no cambia nada: usa streamlit normal)
- services/interprete_ia.py  NUEVO (la función de IA, sacada de views/asistente.py)
- services/ai_client.py      lee secretos de st.secrets O del .env
- services/action_engine.py  1 sola línea cambiada: `from services.estado_voz import st`
- views/asistente.py         ahora importa interpretar_movimiento de interprete_ia (mismo comportamiento)

## .env (solo para la API en tu PC) — agrega los mismos valores que tienes en Streamlit secrets:
    AZURE_OPENAI_ENDPOINT=...
    AZURE_OPENAI_KEY=...
    AZURE_OPENAI_DEPLOYMENT=...
(DATABASE_URL y API_JWT_SECRET ya los tienes.)

## Probar
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    http://localhost:8000/docs  -> debe aparecer POST /voz/comando
