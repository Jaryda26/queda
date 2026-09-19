import tempfile

from services.speech_service import speech_to_text
from services.action_engine import ejecutar_accion

from views.asistente import interpretar_movimiento


def pantalla_voz():

    import streamlit as st

    audio_bytes = st.session_state.get(
        "audio_global"
    )

    if not audio_bytes:
        return None

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
        return "No pude entender el audio."

    resultado = interpretar_movimiento(
        texto
    )

    resultado["texto_original"] = texto

    mensaje = ejecutar_accion(
        resultado
    )

    return mensaje