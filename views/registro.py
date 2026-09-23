import streamlit as st
from services.usuario_service import registrar_usuario


def pantalla_registro():

    st.title("📝 Crear cuenta")

    with st.form("form_registro"):

        nombre = st.text_input("Nombre")
        email = st.text_input("Correo")
        password = st.text_input(
            "Contraseña",
            type="password",
            help="Mínimo 8 caracteres."
        )

        crear = st.form_submit_button("Crear cuenta")

    if crear:

        ok, mensaje = registrar_usuario(nombre, email, password)

        if ok:
            st.success(f"✅ {mensaje} Ya puedes iniciar sesión.")
        else:
            st.error(f"⚠️ {mensaje}")
