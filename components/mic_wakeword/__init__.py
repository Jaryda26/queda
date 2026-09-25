import os

import streamlit.components.v1 as components

_RUTA_COMPONENTE = os.path.dirname(
    os.path.abspath(__file__)
)

_mic_wakeword = components.declare_component(
    "mic_wakeword",
    path=_RUTA_COMPONENTE
)


def mic_wakeword(nombre_activacion, activo=True, key=None):
    """
    Escucha el micrófono de forma continua en el navegador usando
    la Web Speech API nativa (Chrome, Edge, Safari — NO funciona
    en Firefox, que no la soporta). No manda nada a Python hasta
    que detecta que el usuario dijo "nombre_activacion" — ahí sí
    regresa el texto que dijo después, como comando.

    Funciona en dos formas, como un asistente tipo Alexa:
    - "Queda, cuánto llevo gastado" → todo en una frase.
    - "Queda" ... (pausa) ... "cuánto llevo gastado" → el nombre
      solo activa la escucha, y toma la siguiente frase como
      comando.

    Regresa None mientras no haya nada nuevo, o un dict
    {"texto": "...", "ts": <timestamp>} cuando capturó un comando.
    El "ts" sirve para detectar cuándo es un valor nuevo (dedupe
    en el caller, comparando contra el último ts procesado).
    """

    return _mic_wakeword(
        nombre_activacion=nombre_activacion,
        activo=activo,
        key=key,
        default=None
    )
