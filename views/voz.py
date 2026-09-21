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

        # ----------------------------------
        # PRIMERA CAPA:
        # Intent Engine
        # ----------------------------------

        intencion = detectar_intencion(
            texto
        )

        if intencion:

            intencion["texto_original"] = texto

            mensaje = ejecutar_accion(
                intencion
            )

            st.session_state[
                "audio_global"
            ] = None

            return mensaje

        # ----------------------------------
        # SEGUNDA CAPA:
        # Azure OpenAI
        # ----------------------------------

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