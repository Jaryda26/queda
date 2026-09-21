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
        st.write("DEBUG TEXTO:", texto)
        if not texto:

            st.session_state["audio_global"] = None

            return {
                "tipo": "ERROR",
                "mensaje": "⚠ No pude entender el audio."
            }

        st.session_state[
            "ultimo_texto_voz"
        ] = texto

        intencion = detectar_intencion(
            texto
        )
        st.write("DEBUG INTENCION:", intencion)
        if intencion:

            intencion["texto_original"] = texto

            accion = intencion.get(
                "accion",
                ""
            )

            # Navegación

            if accion in [
                "ABRIR_INICIO",
                "ABRIR_DASHBOARD",
                "ABRIR_RECORDATORIOS"
            ]:

                ejecutar_accion(
                    intencion
                )

                st.session_state[
                    "audio_global"
                ] = None

                return {
                    "tipo": "NAVEGACION",
                    "accion": accion
                }

            mensaje = ejecutar_accion(
                intencion
            )

            st.session_state[
                "audio_global"
            ] = None

            return {
                "tipo": "MENSAJE",
                "mensaje": mensaje
            }

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

        return {
            "tipo": "MENSAJE",
            "mensaje": mensaje
        }

    except Exception as e:

        st.session_state[
            "audio_global"
        ] = None

        return {
            "tipo": "ERROR",
            "mensaje": f"❌ Error: {str(e)}"
        }