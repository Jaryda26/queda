import streamlit as st
from db import obtener_dataframe

CARD=lambda title,val,color: f"""
<div style='background:{color};padding:18px;border-radius:12px;color:white;'>
<div style='font-size:14px'>{title}</div>
<div style='font-size:38px;font-weight:bold'>{val}</div>
</div>
"""

def pantalla_dashboard():
    uid=st.session_state['user_id']
    i=obtener_dataframe(f"select coalesce(sum(monto),0) total from gastos.movimientos where tipo='INGRESO' and usuario_id={uid}")
    g=obtener_dataframe(f"select coalesce(sum(monto),0) total from gastos.movimientos where tipo='GASTO' and usuario_id={uid}")
    p=obtener_dataframe(f"select monto,tipo_periodo from gastos.presupuestos where usuario_id={uid} order by id desc limit 1")

    ing=float(i.iloc[0]['total'])
    gas=float(g.iloc[0]['total'])
    pres=float(p.iloc[0]['monto']) if not p.empty else 0
    disp=ing-gas
    pct=(gas/pres*100) if pres>0 else 0

    c1,c2,c3,c4,c5=st.columns(5)
    with c1: st.markdown(CARD('Disponible',f'$ {disp:,.0f}','#4CAF50'),unsafe_allow_html=True)
    with c2: st.markdown(CARD('Ingresos',f'$ {ing:,.0f}','#36CFC9'),unsafe_allow_html=True)
    with c3: st.markdown(CARD('Gastos',f'$ {gas:,.0f}','#4A90E2'),unsafe_allow_html=True)
    with c4: st.markdown(CARD('Presupuesto',f'$ {pres:,.0f}','#F5A623'),unsafe_allow_html=True)
    with c5: st.markdown(CARD('% Utilizado',f'{pct:.1f}%','#57C0E8'),unsafe_allow_html=True)

    st.subheader('Últimos movimientos')
    ult=obtener_dataframe(f"select fecha,concepto,tipo,monto from gastos.movimientos where usuario_id={uid} order by fecha desc limit 10")
    st.dataframe(ult,use_container_width=True)
