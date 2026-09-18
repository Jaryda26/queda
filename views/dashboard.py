import streamlit as st
import plotly.express as px
import pandas as pd
from db import obtener_dataframe

CARD=lambda t,v,c:f"<div style='background:{c};padding:18px;border-radius:12px;color:white'><div>{t}</div><div style='font-size:32px;font-weight:bold'>{v}</div></div>"

def pantalla_dashboard():
    uid=st.session_state['user_id']
    i=obtener_dataframe(f"select coalesce(sum(monto),0) total from gastos.movimientos where tipo='INGRESO' and usuario_id={uid}")
    g=obtener_dataframe(f"select coalesce(sum(monto),0) total from gastos.movimientos where tipo='GASTO' and usuario_id={uid}")
    p=obtener_dataframe(f"select monto from gastos.presupuestos where usuario_id={uid} order by id desc limit 1")

    ing=float(i.iloc[0]['total'])
    gas=float(g.iloc[0]['total'])
    pres=float(p.iloc[0]['monto']) if not p.empty else 0
    disp=ing-gas
    pct=(gas/pres*100) if pres>0 else 0

    c1,c2,c3,c4,c5=st.columns(5)
    c1.markdown(CARD('Disponible',f'$ {disp:,.0f}','#2ecc71'),unsafe_allow_html=True)
    c2.markdown(CARD('Ingresos',f'$ {ing:,.0f}','#1abc9c'),unsafe_allow_html=True)
    c3.markdown(CARD('Gastos',f'$ {gas:,.0f}','#3498db'),unsafe_allow_html=True)
    c4.markdown(CARD('Presupuesto',f'$ {pres:,.0f}','#f39c12'),unsafe_allow_html=True)
    c5.markdown(CARD('% Utilizado',f'{pct:.1f}%','#9b59b6'),unsafe_allow_html=True)

    st.markdown('---')

    col1,col2=st.columns(2)

    with col1:
      graf=pd.DataFrame({'Concepto':['Ingresos','Gastos'],'Monto':[ing,gas]})
      fig=px.bar(graf,x='Concepto',y='Monto',title='Ingresos vs Gastos',color='Concepto')
      st.plotly_chart(fig,use_container_width=True)

    with col2:
      cat=obtener_dataframe(f"select coalesce(categoria,'Sin categoría') categoria,sum(monto) monto from gastos.movimientos where tipo='GASTO' and usuario_id={uid} group by categoria")
      if not cat.empty:
        fig2=px.pie(cat,names='categoria',values='monto',hole=.6,title='Gastos por Categoría')
        st.plotly_chart(fig2,use_container_width=True)

    st.markdown('### Resumen Inteligente')
    st.info(f'Te quedan $ {disp:,.0f} disponibles. Has utilizado {pct:.1f}% de tu presupuesto.')

    ult=obtener_dataframe(f"select fecha,concepto,tipo,monto from gastos.movimientos where usuario_id={uid} order by fecha desc limit 10")
    st.markdown('### Últimos movimientos')
    st.dataframe(ult,use_container_width=True)
