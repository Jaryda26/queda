import tempfile
import streamlit as st

from audio_recorder_streamlit import audio_recorder

from services.speech_service import speech_to_text
from services.action_engine import ejecutar_accion

from views.asistente import interpretar_movimiento


def pantalla_voz():

    st.title("🎤 Queda")

    st.markdown(
        """
### Habla naturalmente

Ejemplos:

- Compré una coca de 25 pesos
- Gasté 350 en gasolina
- Ya pagué Sears
- Muéstrame estadísticas
- Qué tengo pendiente
- Me depositaron 12000 de nómina
"""
    )

    audio_bytes = st.session_state.get(
        "audio_global"
    )

    if not audio_bytes:

        st.info(
            "Presiona el micrófono para comenzar."
        )

        return

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as tmp:

            tmp.write(audio_bytes)

            archivo_audio = tmp.name

        st.success(
            "✅ Audio capturado"
        )

        texto = speech_to_text(
            archivo_audio
        )

        if not texto:

            st.warning(
                "No pude reconocer el audio."
            )

            return

        st.markdown(
            "### Texto reconocido"
        )

        st.write(texto)

        resultado = interpretar_movimiento(
            texto
        )

        resultado["texto_original"] = texto

        mensaje = ejecutar_accion(
            resultado
        )

        st.success(
            mensaje
        )

        st.session_state["audio_global"] = None

    except Exception as e:

        st.error(
            f"Error: {str(e)}"
        )