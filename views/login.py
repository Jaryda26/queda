import streamlit as st

from services.usuario_service import validar_usuario
from auth.session import login_user


def pantalla_login():

    st.title("🔐 Login")

    with st.form("form_login"):

        email = st.text_input(
            "Correo"
        )

        password = st.text_input(
            "Contraseña",
            type="password"
        )

        entrar = st.form_submit_button(
            "Entrar"
        )

    if entrar:

        usuario = validar_usuario(
            email,
            password
        )

        if usuario is not None:

            login_user(
                int(usuario["id"]),
                usuario["nombre"],
                usuario["email"]
            )

            st.rerun()

        else:

            st.error(
                "Credenciales inválidas"
            )