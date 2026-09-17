import streamlit as st
from db import ejecutar_query

def pantalla_movimientos():
 st.title('Movimientos')
 t=st.selectbox('Tipo',['INGRESO','GASTO'])
 c=st.text_input('Concepto')
 m=st.number_input('Monto',min_value=0.0)
 if st.button('Guardar Movimiento'):
  ejecutar_query('insert into gastos.movimientos(usuario_id,tipo,concepto,monto) values(:u,:t,:c,:m)',{'u':st.session_state['user_id'],'t':t,'c':c,'m':m})
  st.success('Guardado')
