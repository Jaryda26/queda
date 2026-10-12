import os

import streamlit as st
from openai import OpenAI


def _secreto(nombre):
    """
    Lee un secreto de st.secrets (Streamlit Cloud) y, si no está ahí
    (por ejemplo cuando corre la API del celular con uvicorn), de las
    variables de entorno / .env. Lanza KeyError si no existe en ninguno.
    """

    try:
        return st.secrets[nombre]
    except Exception:
        pass

    valor = os.getenv(nombre)

    if valor:
        return valor

    raise KeyError(nombre)

_client = None


def get_openai_client():
    """
    Devuelve un cliente de Azure OpenAI ya configurado, reutilizando
    la misma instancia durante la sesión de Streamlit.

    Se inicializa de forma perezosa (solo cuando alguien realmente
    lo necesita) para que la app no truene al arrancar si todavía
    no configuraste las credenciales en st.secrets.
    """

    global _client

    if _client is not None:
        return _client

    try:

        endpoint = _secreto("AZURE_OPENAI_ENDPOINT")
        api_key = _secreto("AZURE_OPENAI_KEY")

    except Exception:

        raise RuntimeError(
            "Faltan las credenciales de Azure OpenAI en st.secrets "
            "(AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY)."
        )

    _client = OpenAI(
        base_url=endpoint,
        api_key=api_key
    )

    return _client


def get_deployment():
    """Nombre del deployment configurado en st.secrets."""

    return _secreto("AZURE_OPENAI_DEPLOYMENT")
