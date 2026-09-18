import streamlit as st

from views.login import pantalla_login
from views.registro import pantalla_registro
from views.dashboard import pantalla_dashboard
from views.movimientos import pantalla_movimientos
from views.historial import pantalla_historial
from views.presupuesto import pantalla_presupuesto
from views.asistente import pantalla_asistente
from views.voz import pantalla_voz

st.set_page_config(
    page_title="Queda",
    page_icon="💰",
    layout="wide"
)

if "user_id" not in st.session_state:

    op = st.sidebar.radio(
        "Acceso",
        [
            "Login",
            "Registro"
        ]
    )

    if op == "Login":
        pantalla_login()
    else:
        pantalla_registro()

else:

    st.sidebar.success(
        st.session_state.get("nombre", "")
    )

    op = st.sidebar.radio(
        "Menú",
        [
            "Dashboard",
            "Movimientos",
            "Historial",
            "Presupuesto",
            "Asistente IA",
            "Captura Voz"
        ]
    )

    if st.sidebar.button(
        "Cerrar Sesión"
    ):
        st.session_state.clear()
        st.rerun()

    paginas = {
        "Dashboard": pantalla_dashboard,
        "Movimientos": pantalla_movimientos,
        "Historial": pantalla_historial,
        "Presupuesto": pantalla_presupuesto,
        "Asistente IA": pantalla_asistente,
        "Captura Voz": pantalla_voz
    }

    paginas[op]()
