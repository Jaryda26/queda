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

Todavía NO se registra gasto.
"""
    )

    audio_bytes = audio_recorder()

    if audio_bytes:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as tmp:

            tmp.write(audio_bytes)

            audio_file = tmp.name

        st.success(
            "✅ Audio capturado"
        )

        try:

            texto = speech_to_text(
                audio_file
            )

            st.success(
                "✅ Texto reconocido"
            )

            st.text_area(
                "Resultado",
                texto,
                height=120
            )

        except Exception as e:

            st.error(
                f"Error Speech: {str(e)}"
            )