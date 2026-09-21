import tempfile
import streamlit as st
import azure.cognitiveservices.speech as speechsdk


def texto_a_voz(texto):

    speech_config = speechsdk.SpeechConfig(
        subscription=st.secrets["AZURE_SPEECH_KEY"],
        region=st.secrets["AZURE_SPEECH_REGION"]
    )

    speech_config.speech_synthesis_voice_name = (
        "es-MX-DaliaNeural"
    )

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