import tempfile
import streamlit as st

from services.speech_service import speech_to_text
from services.action_engine import ejecutar_accion

from views.asistente import interpretar_movimiento


def pantalla_voz():

    audio_bytes = st.session_state.get(
        "audio_global"
    )

    if not audio_bytes:

        st.warning(
            "No hay audio disponible."
        )

        return

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

            st.warning(
                "No pude reconocer el audio."
            )

            st.session_state["audio_global"] = None

            return

        resultado = interpretar_movimiento(
            texto
        )

        resultado["texto_original"] = texto

        mensaje = ejecutar_accion(
            resultado
        )

        st.success(mensaje)

        st.session_state["audio_global"] = None

    except Exception as e:

        st.error(
            f"ERROR: {str(e)}"
        )

        st.session_state["audio_global"] = None