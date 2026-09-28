import tempfile
import streamlit as st
import azure.cognitiveservices.speech as speechsdk


VOCES_DISPONIBLES = {
    "femenina": "es-MX-DaliaNeural",
    "masculina": "es-MX-JorgeNeural"
}


def texto_a_voz(texto, voz="femenina"):

    nombre_voz = VOCES_DISPONIBLES.get(
        voz,
        VOCES_DISPONIBLES["femenina"]
    )

    speech_config = speechsdk.SpeechConfig(
        subscription=st.secrets["AZURE_SPEECH_KEY"],
        region=st.secrets["AZURE_SPEECH_REGION"]
    )

    speech_config.speech_synthesis_voice_name = nombre_voz

    archivo = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".wav"
    )

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=archivo.name
    )

    sintetizador = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    sintetizador.speak_text_async(
        texto
    ).get()

    return archivo.name