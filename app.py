import streamlit as st

from views.login import pantalla_login
from views.registro import pantalla_registro

from views.home import pantalla_home

from views.dashboard import pantalla_dashboard
from views.movimientos import pantalla_movimientos
from views.historial import pantalla_historial
from views.presupuesto import pantalla_presupuesto
from views.recordatorios import pantalla_recordatorios
from views.asistente import pantalla_asistente
from views.voz import pantalla_voz

st.set_page_config(
    page_title="Queda",
    page_icon="💰",
    layout="wide"
)

# Primera pantalla después del login
if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = "🏠 Inicio"

# Usuario NO autenticado
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

# Usuario autenticado
else:

    st.sidebar.success(
        st.session_state.get(
            "nombre",
            ""
        )
    )
    st.sidebar.markdown("---")

    if st.sidebar.button("🎤 Hablar con Queda"):

            st.session_state["pagina_actual"] = (
                "Captura Voz"
            )

            st.rerun()

    st.sidebar.markdown("---")
    
    menu = [
        "🏠 Inicio",
        "Dashboard",
        "Movimientos",
        "Historial",
        "Presupuesto",
        "Recordatorios",
        "Asistente IA",
        "Captura Voz"
    ]

    try:
        indice = menu.index(
            st.session_state["pagina_actual"]
        )
    except Exception:
        indice = 0

    op = st.sidebar.radio(
        "Menú",
        menu,
        index=indice
    )

    st.session_state["pagina_actual"] = op

    if st.sidebar.button(
        "Cerrar Sesión"
    ):

        st.session_state.clear()

        st.rerun()

    paginas = {
        "🏠 Inicio": pantalla_home,
        "Dashboard": pantalla_dashboard,
        "Movimientos": pantalla_movimientos,
        "Historial": pantalla_historial,
        "Presupuesto": pantalla_presupuesto,
        "Recordatorios": pantalla_recordatorios,
        "Asistente IA": pantalla_asistente,
        "Captura Voz": pantalla_voz
    }

    paginas[op]()