import tempfile
import streamlit as st

from services.speech_service import speech_to_text
from services.intent_engine import detectar_intencion
from services.action_engine import ejecutar_accion

from views.asistente import interpretar_movimiento


def pantalla_voz():

    audio_bytes = st.session_state.get(
        "audio_global"
    )

    if not audio_bytes:
        return None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as tmp:

            tmp.write(audio_bytes)

            archivo_audio = tmp.name

        texto = speech_to_text(
            archivo_audio
        )

        if not texto:

            st.session_state["audio_global"] = None

            return "⚠ No pude entender el audio."

        # Guardamos el último comando para depuración
        st.session_state[
            "ultimo_texto_voz"
        ] = texto

        intencion = detectar_intencion(
            texto
        )

        if intencion:

            intencion["texto_original"] = texto

            accion = intencion.get(
                "accion",
                ""
            )

            # NAVEGACIÓN
            if accion == "ABRIR_DASHBOARD":

                st.session_state[
                    "pagina_actual"
                ] = "Dashboard"

                st.session_state[
                    "audio_global"
                ] = None

                st.rerun()

            if accion == "ABRIR_RECORDATORIOS":

                st.session_state[
                    "pagina_actual"
                ] = "Recordatorios"

                st.session_state[
                    "audio_global"
                ] = None

                st.rerun()

            if accion == "ABRIR_INICIO":

                st.session_state[
                    "pagina_actual"
                ] = "🏠 Inicio"

                st.session_state[
                    "audio_global"
                ] = None

                st.rerun()

            # RESTO DE ACCIONES
            mensaje = ejecutar_accion(
                intencion
            )

            st.session_state[
                "audio_global"
            ] = None

            return mensaje

        # IA

        resultado = interpretar_movimiento(
            texto
        )

        resultado["texto_original"] = texto

        mensaje = ejecutar_accion(
            resultado
        )

        st.session_state[
            "audio_global"
        ] = None

        return mensaje

    except Exception as e:

        st.session_state[
            "audio_global"
        ] = None

        return f"❌ Error: {str(e)}"