import streamlit as st


def login_user(usuario_id, nombre, email, cuenta_id, rol_cuenta):

    st.session_state["user_id"] = usuario_id
    st.session_state["nombre"] = nombre
    st.session_state["nombre_corto"] = nombre.split()[0]
    st.session_state["email"] = email
    st.session_state["cuenta_id"] = cuenta_id
    st.session_state["rol_cuenta"] = rol_cuenta
