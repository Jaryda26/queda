import streamlit as st
def login_user(i,n,e):
 st.session_state['user_id']=i;st.session_state['nombre']=n;st.session_state['email']=e
