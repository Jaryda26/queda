"""
Estado de sesión para el motor de acciones (action_engine).

- En la WEB (Streamlit) `st` es el streamlit de siempre: nada cambia.
- En la API del celular (QUEDA_API=1) `st` es un sustituto liviano:
    * session_state = diccionario propio de CADA petición (por hilo),
      así dos usuarios hablando a la vez nunca se mezclan.
    * rerun() = en vez de recargar la página, avisa "navega a X".
"""

import os

if os.getenv("QUEDA_API") == "1":

    import threading

    class NavegarSolicitado(Exception):
        """Se lanzó un st.rerun() tras fijar pagina_actual."""

    _local = threading.local()

    def nueva_sesion(**datos):
        _local.estado = dict(datos)
        return _local.estado

    class _StAPI:

        @property
        def session_state(self):
            return _local.estado

        @staticmethod
        def rerun():
            raise NavegarSolicitado()

    st = _StAPI()

else:

    import streamlit as st

    class NavegarSolicitado(Exception):
        pass

    def nueva_sesion(**datos):
        raise RuntimeError("Solo se usa en la API (QUEDA_API=1)")
