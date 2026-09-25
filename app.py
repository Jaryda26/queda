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
from views.voz import pantalla_voz, procesar_texto_voz
from views.aprendizaje import pantalla_aprendizaje
from views.suscripcion import pantalla_suscripcion
from views.cuenta import pantalla_cuenta

from services.billing_service import tiene_suscripcion_activa
from services.usuario_service import (
    validar_token_sesion,
    invalidar_token_sesion
)
from auth.session import login_user
from components.mic_wakeword import mic_wakeword
from services.ui_theme import aplicar_tema
from services.tts_service import texto_a_voz

import extra_streamlit_components as stx


st.set_page_config(
    page_title="Queda",
    page_icon="💰",
    layout="wide"
)

aplicar_tema()

cookie_manager = stx.CookieManager(
    key="queda_cookie_manager"
)


def _cerrar_sesion():
    """
    Cierra sesión de verdad: borra el token guardado en la base
    (para que la cookie vieja, si alguien la copia, ya no sirva)
    y borra la cookie del navegador — no solo el session_state,
    que de todas formas Streamlit reinicia solo.
    """

    if st.session_state.get("user_id"):

        try:

            invalidar_token_sesion(
                st.session_state["user_id"]
            )

        except Exception:
            pass

    try:

        cookie_manager.delete(
            "queda_token",
            key="borrar_queda_token"
        )

    except Exception:
        pass

    st.session_state.clear()

    st.rerun()


def _hablar_respuesta(texto):
    """
    Convierte la respuesta del asistente a voz y la reproduce —
    para que de verdad "converse" contigo cuando le hablas, no
    solo cuando entras a la app. Nunca debe romper el flujo si
    Azure Speech falla (sin credenciales, sin cuota, etc.) — en
    ese caso simplemente no se escucha nada, pero el mensaje de
    texto ya se mostró de todas formas.
    """

    try:

        archivo_audio = texto_a_voz(texto)

        st.sidebar.audio(
            archivo_audio,
            format="audio/wav",
            autoplay=True
        )

    except Exception:
        pass

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
# SESIÓN PERSISTENTE ("recuérdame")
# =====================================================
# Streamlit borra st.session_state cada vez que el navegador abre
# una conexión nueva (cerrar/reabrir la pestaña, o a veces solo
# navegar y volver) — por diseño no sobrevive eso. Para no pedir
# login cada vez, guardamos un token en una cookie del navegador
# (30 días) al iniciar sesión, y aquí, si no hay sesión activa
# pero SÍ hay una cookie con un token válido, restauramos la
# sesión sin pedir contraseña otra vez.

if "user_id" not in st.session_state:

    token_guardado = cookie_manager.get(
        "queda_token"
    )

    if token_guardado:

        try:

            usuario_guardado = validar_token_sesion(
                token_guardado
            )

        except Exception:

            # Si la base todavía no tiene las columnas de sesión
            # persistente (falta correr sql/schema.sql), esto
            # NUNCA debe tapar la pantalla de login — se ignora y
            # sigue como si no hubiera cookie.

            usuario_guardado = None

        if (
            usuario_guardado is not None
            and usuario_guardado.get("cuenta_id") is not None
        ):

            login_user(
                int(usuario_guardado["id"]),
                usuario_guardado["nombre"],
                usuario_guardado["email"],
                int(usuario_guardado["cuenta_id"]),
                usuario_guardado.get(
                    "rol_cuenta",
                    "ADMIN"
                ),
                usuario_guardado.get(
                    "nombre_agente",
                    "Queda"
                )
            )

            st.rerun()

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
        pantalla_login(cookie_manager)
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

            _cerrar_sesion()

        pantalla_suscripcion()

        st.stop()

    st.sidebar.markdown("### 🎤 Queda")

    audio_bytes = audio_recorder(
        text="",
        recording_color="#e74c3c",
        neutral_color="#2c3e50",
        icon_name="microphone",
        icon_size="5x"
    )

    # =====================================
    # ACTIVACIÓN POR VOZ (beta) — nivel 1:
    # escucha continua en el navegador, se
    # activa diciendo el nombre elegido, y
    # se corta sola al terminar de hablar.
    # Solo funciona en Chrome/Edge/Safari
    # (la Web Speech API no existe en
    # Firefox) — por eso queda apagado por
    # default y hay que prenderlo a mano.
    # =====================================

    activacion_voz = st.sidebar.toggle(
        "🗣️ Activación por voz (beta)",
        value=st.session_state.get(
            "activacion_voz_encendida",
            False
        ),
        help=(
            "Solo funciona en Chrome, Edge o Safari. "
            "Requiere dar permiso de micrófono una vez."
        )
    )

    st.session_state[
        "activacion_voz_encendida"
    ] = activacion_voz

    if activacion_voz:

        resultado_wakeword = mic_wakeword(
            nombre_activacion=st.session_state.get(
                "nombre_agente",
                "Queda"
            ),
            activo=True,
            key="mic_wakeword"
        )

        if (
            isinstance(resultado_wakeword, dict)
            and resultado_wakeword.get("ts")
            != st.session_state.get(
                "ultimo_ts_wakeword"
            )
        ):

            st.session_state[
                "ultimo_ts_wakeword"
            ] = resultado_wakeword["ts"]

            try:

                respuesta_wakeword = procesar_texto_voz(
                    resultado_wakeword["texto"]
                )

                if (
                    respuesta_wakeword.get("tipo")
                    == "MENSAJE"
                ):

                    st.sidebar.success(
                        respuesta_wakeword["mensaje"]
                    )

                    _hablar_respuesta(
                        respuesta_wakeword["mensaje"]
                    )

                elif (
                    respuesta_wakeword.get("tipo")
                    == "ERROR"
                ):

                    st.sidebar.error(
                        respuesta_wakeword["mensaje"]
                    )

                if respuesta_wakeword.get("tipo") in (
                    "MENSAJE",
                    "ERROR"
                ):

                    st.rerun()

            except Exception as e:

                st.sidebar.error(str(e))

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

                    _hablar_respuesta(
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

        _cerrar_sesion()

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