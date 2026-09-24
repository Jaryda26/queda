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
from views.aprendizaje import pantalla_aprendizaje
from views.suscripcion import pantalla_suscripcion
from views.cuenta import pantalla_cuenta

from services.billing_service import tiene_suscripcion_activa
from services.ui_theme import aplicar_tema


st.set_page_config(
    page_title="Queda",
    page_icon="💰",
    layout="wide"
)

aplicar_tema()

# =====================================================
# ESTADO GLOBAL
# =====================================================

if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = "🏠 Inicio"

if "audio_global" not in st.session_state:
    st.session_state["audio_global"] = None

if "ultimo_audio_hash" not in st.session_state:
    st.session_state["ultimo_audio_hash"] = None

if "debug_accion" not in st.session_state:
    st.session_state["debug_accion"] = ""

# =====================================================
# LOGIN
# =====================================================

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

# =====================================================
# USUARIO AUTENTICADO
# =====================================================

else:

    cuenta_id = st.session_state["cuenta_id"]

    st.sidebar.success(
        st.session_state.get(
            "nombre",
            ""
        )
    )

    st.sidebar.markdown("---")

    # =====================================
    # PAYWALL: sin plan activo, solo puede
    # ver/elegir un plan o cerrar sesión.
    # =====================================

    if not tiene_suscripcion_activa(cuenta_id):

        st.sidebar.warning(
            "Activa un plan para usar Queda."
        )

        if st.sidebar.button(
            "Cerrar Sesión",
            use_container_width=True
        ):

            st.session_state.clear()

            st.rerun()

        pantalla_suscripcion()

        st.stop()

    st.sidebar.markdown("### 🎤 Queda")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e74c3c",
        neutral_color="#2c3e50",
        icon_name="microphone",
        icon_size="2x"
    )

    # =====================================
    # PROCESAMIENTO DE VOZ
    # =====================================

    if audio_bytes:

        st.session_state["audio_global"] = (
            audio_bytes
        )

        try:

            respuesta = pantalla_voz()

            if isinstance(
                respuesta,
                dict
            ):
                
                if (
                    respuesta.get("tipo")
                    == "NAVEGACION"
                ):

                    accion = respuesta.get(
                        "accion",
                        ""
                    )

                    if accion == "ABRIR_INICIO":

                        st.session_state[
                            "pagina_actual"
                        ] = "🏠 Inicio"

                    elif accion == "ABRIR_DASHBOARD":

                        st.session_state[
                            "pagina_actual"
                        ] = "Dashboard"

                    elif (
                        accion
                        ==
                        "ABRIR_RECORDATORIOS"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "Recordatorios"

                    elif (
                        accion
                        ==
                        "ABRIR_PRESUPUESTO"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "Presupuesto"

                    elif (
                        accion
                        ==
                        "ABRIR_HISTORIAL"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "Historial"

                    elif (
                        accion
                        ==
                        "ABRIR_MOVIMIENTOS"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "Movimientos"

                    elif (
                        accion
                        ==
                        "ABRIR_APRENDIZAJE"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "🧠 Aprendizaje"

                    elif (
                        accion
                        ==
                        "ABRIR_ASISTENTE"
                    ):

                        st.session_state[
                            "pagina_actual"
                        ] = "Asistente IA"

                    st.session_state[
                        "audio_global"
                    ] = None
                    
                    st.rerun()

                elif (
                    respuesta.get("tipo")
                    == "MENSAJE"
                ):

                    st.sidebar.success(
                        respuesta["mensaje"]
                    )

                elif (
                    respuesta.get("tipo")
                    == "ERROR"
                ):

                    if (
                        respuesta["mensaje"]
                        !=
                        "⚠ Audio ya procesado."
                    ):

                        st.sidebar.error(
                            respuesta["mensaje"]
                        )

        except Exception as e:

            st.sidebar.error(
                str(e)
            )

    st.sidebar.markdown("---")

    menu = [
        "🏠 Inicio",
        "Dashboard",
        "Movimientos",
        "Historial",
        "Presupuesto",
        "Recordatorios",
        "Asistente IA",
        "🧠 Aprendizaje",
        "👨‍👩‍👧 Cuenta",
        "💳 Suscripción"
    ]

    if (
        "menu_principal"
        not in st.session_state
    ):

        st.session_state[
            "menu_principal"
        ] = st.session_state[
            "pagina_actual"
        ]

    if (
        "pagina_sincronizada"
        not in st.session_state
    ):

        st.session_state[
            "pagina_sincronizada"
        ] = st.session_state[
            "pagina_actual"
        ]

    # Sincronización automática:
    # solo forzamos el radio cuando "pagina_actual"
    # cambió por fuera del propio radio (ej. por voz),
    # es decir, cuando ya no coincide con la última
    # página que sincronizamos. Así no pisamos un clic
    # manual que el usuario acaba de hacer en el radio.

    if (
        st.session_state["pagina_actual"]
        !=
        st.session_state["pagina_sincronizada"]
    ):

        st.session_state[
            "menu_principal"
        ] = st.session_state[
            "pagina_actual"
        ]

        st.session_state[
            "pagina_sincronizada"
        ] = st.session_state[
            "pagina_actual"
        ]

    opcion = st.sidebar.radio(
        "Menú",
        menu,
        key="menu_principal"
    )

    # Si el usuario cambió el radio manualmente,
    # "opcion" ya trae el nuevo valor: lo reflejamos
    # en pagina_actual y en el snapshot de sincronía.

    if opcion != st.session_state["pagina_actual"]:

        st.session_state[
            "pagina_actual"
        ] = opcion

        st.session_state[
            "pagina_sincronizada"
        ] = opcion

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
            pantalla_asistente,

        "🧠 Aprendizaje":
            pantalla_aprendizaje,

        "👨‍👩‍👧 Cuenta":
            pantalla_cuenta,

        "💳 Suscripción":
            pantalla_suscripcion
    }

    paginas[
        st.session_state["pagina_actual"]
    ]()