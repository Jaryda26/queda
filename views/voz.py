import tempfile
import streamlit as st

from audio_recorder_streamlit import audio_recorder
from services.speech_service import speech_to_text


def pantalla_voz():

    st.title("🎤 Registro por Voz")

    st.info(
        """
Primer paso:

Vamos a convertir voz en texto.
"""
    )

    audio_bytes = audio_recorder()

    if audio_bytes:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as tmp:

            tmp.write(audio_bytes)

            archivo_audio = tmp.name

        st.success("✅ Audio capturado")

        texto = speech_to_text(
            archivo_audio
        )

        st.success("✅ Respuesta Speech recibida")

        st.write("Resultado recibido:")

        st.code(texto)