import streamlit as st
from views.login import pantalla_login
from views.registro import pantalla_registro
from views.dashboard import pantalla_dashboard
from views.movimientos import pantalla_movimientos
from views.historial import pantalla_historial
from views.presupuesto import pantalla_presupuesto

st.set_page_config(page_title="Queda",page_icon="💰",layout="wide")
if "user_id" not in st.session_state:
    op=st.sidebar.radio("Acceso",["Login","Registro"])
    pantalla_login() if op=="Login" else pantalla_registro()
else:
    st.sidebar.success(st.session_state.get("nombre",""))
    op=st.sidebar.radio("Menú",["Dashboard","Movimientos","Historial","Presupuesto","Asistente IA"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()
    {'Dashboard':pantalla_dashboard,'Movimientos':pantalla_movimientos,'Historial':pantalla_historial,'Presupuesto':pantalla_presupuesto}[op]()
