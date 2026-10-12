import os

# Debe fijarse ANTES de importar services.action_engine: le dice al motor de
# acciones que corre en la API (sin Streamlit) y no en la web.
os.environ["QUEDA_API"] = "1"
