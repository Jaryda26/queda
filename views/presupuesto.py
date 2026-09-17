import streamlit as st
from datetime import date,timedelta
from db import ejecutar_query,obtener_dataframe

def pantalla_presupuesto():
 uid=st.session_state['user_id']
 st.title('Presupuesto')
 tipo=st.selectbox('Periodo',['SEMANAL','QUINCENAL','MENSUAL'])
 monto=st.number_input('Monto',min_value=0.0)
 if st.button('Guardar Presupuesto'):
  dias={'SEMANAL':7,'QUINCENAL':15,'MENSUAL':30}[tipo]
  ejecutar_query('insert into gastos.presupuestos(usuario_id,tipo_periodo,monto,fecha_inicio,fecha_fin) values(:u,:t,:m,:i,:f)',{'u':uid,'t':tipo,'m':m,'i':date.today(),'f':date.today()+timedelta(days=dias)})
  st.success('Presupuesto guardado')
 cur=obtener_dataframe(f"select * from gastos.presupuestos where usuario_id={uid} order by id desc limit 1")
 if not cur.empty: st.dataframe(cur,use_container_width=True)
