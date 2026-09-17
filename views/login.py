import streamlit as st
from services.usuario_service import validar_usuario
from auth.session import login_user

def pantalla_login():
 st.title("Login")
 e=st.text_input("Correo")
 p=st.text_input("Contraseña",type="password")
 if st.button("Entrar"):
  u=validar_usuario(e,p)
  if u is not None: login_user(int(u['id']),u['nombre'],u['email']); st.rerun()
  else: st.error("Credenciales inválidas")
