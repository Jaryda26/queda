import streamlit as st
from db import ejecutar_query

def pantalla_movimientos():
 st.title('Movimientos')
 tipo=st.selectbox('Tipo',['INGRESO','GASTO'])
 categoria=st.selectbox('Categoría',['Gasolina','Comida','Servicios','Transporte','Salud','Entretenimiento','Otros'])
 concepto=st.text_input('Concepto')
 monto=st.number_input('Monto',min_value=0.0)
 if st.button('Guardar Movimiento'):
  ejecutar_query('insert into gastos.movimientos(usuario_id,tipo,categoria,concepto,monto) values(:u,:t,:cat,:c,:m)',{'u':st.session_state['user_id'],'t':tipo,'cat':categoria,'c':concepto,'m':m})
  st.success('Guardado')
