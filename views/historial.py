import streamlit as st
from db import obtener_dataframe

def pantalla_historial():
 uid=st.session_state['user_id']
 df=obtener_dataframe(f"select fecha,tipo,concepto,monto from gastos.movimientos where usuario_id={uid} order by fecha desc")
 st.title('Historial')
 st.dataframe(df,use_container_width=True)
