import streamlit as st
import azure.cognitiveservices.speech as speechsdk


def speech_to_text(audio_file):

    speech_config = speechsdk.SpeechConfig(
        subscription=st.secrets["AZURE_SPEECH_KEY"],
        region=st.secrets["AZURE_SPEECH_REGION"]
    )

    speech_config.speech_recognition_language = "es-MX"

    audio_config = speechsdk.audio.AudioConfig(
        filename=audio_file
    )

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:

        return result.text

    if result.reason == speechsdk.ResultReason.NoMatch:

        return None

    if result.reason == speechsdk.ResultReason.Canceled:

        return None

    return None