import streamlit as st
from services.usuario_service import registrar_usuario

def pantalla_registro():
 st.title("Registro")
 n=st.text_input("Nombre")
 e=st.text_input("Correo")
 p=st.text_input("Contraseña",type="password")
 if st.button("Crear cuenta"):
  registrar_usuario(n,e,p); st.success("Usuario creado")
