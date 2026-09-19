import streamlit as st

from audio_recorder_streamlit import audio_recorder

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

if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = "🏠 Inicio"

if "audio_global" not in st.session_state:
    st.session_state["audio_global"] = None

if "user_id" not in st.session_state:

    opcion = st.sidebar.radio(
        "Acceso",
        [
            "Login",
            "Registro"
        ]
    )

    if opcion == "Login":
        pantalla_login()
    else:
        pantalla_registro()

else:

    st.sidebar.success(
        st.session_state.get(
            "nombre",
            ""
        )
    )

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🎤 Queda")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e74c3c",
        neutral_color="#2c3e50",
        icon_name="microphone",
        icon_size="2x"
    )

    if audio_bytes:

        st.session_state["audio_global"] = audio_bytes

        st.session_state["pagina_actual"] = "Voz"

        st.rerun()

    st.sidebar.markdown("---")

    menu = [
        "🏠 Inicio",
        "Dashboard",
        "Movimientos",
        "Historial",
        "Presupuesto",
        "Recordatorios",
        "Asistente IA"
    ]

    try:

        indice = menu.index(
            st.session_state["pagina_actual"]
        )

    except Exception:

        indice = 0

    opcion = st.sidebar.radio(
        "Menú",
        menu,
        index=indice
    )

    if st.session_state["pagina_actual"] == "Voz":

        pantalla_voz()

        st.session_state["pagina_actual"] = "🏠 Inicio"

        st.stop()

    st.session_state["pagina_actual"] = opcion

    st.sidebar.markdown("---")

    if st.sidebar.button(
        "Cerrar Sesión",
        use_container_width=True
    ):

        st.session_state.clear()
        st.rerun()

    paginas = {

        "🏠 Inicio":
            pantalla_home,

        "Dashboard":
            pantalla_dashboard,

        "Movimientos":
            pantalla_movimientos,

        "Historial":
            pantalla_historial,

        "Presupuesto":
            pantalla_presupuesto,

        "Recordatorios":
            pantalla_recordatorios,

        "Asistente IA":
            pantalla_asistente
    }

    paginas[opcion]()