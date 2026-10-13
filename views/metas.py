import streamlit as st

from services import metas_service as ms


def pantalla_metas():

    uid = st.session_state["user_id"]
    cuenta_id = st.session_state["cuenta_id"]

    st.title("🎯 Metas de ahorro")

    st.caption(
        "Un abono no es un gasto: no mueve tu presupuesto, solo avanza "
        "la meta. También puedes decir: quiero ahorrar 10 mil pesos "
        "para vacaciones, o: abona 500 a vacaciones."
    )

    try:
        metas = ms.listar_metas(cuenta_id)
    except Exception:
        st.error(
            "No pude cargar tus metas. Falta correr sql/metas_ia.sql "
            "en Supabase."
        )
        return

    with st.expander("➕ Nueva meta", expanded=not metas):

        with st.form("form_meta", clear_on_submit=True):

            nombre = st.text_input("¿Para qué quieres ahorrar?")

            monto = st.number_input(
                "Monto objetivo",
                min_value=0.0,
                step=500.0
            )

            usa_fecha = st.checkbox("Tengo una fecha límite")

            fecha = st.date_input("Fecha límite")

            if st.form_submit_button("Crear meta"):

                try:

                    from datetime import date

                    ms.crear_meta(
                        uid,
                        cuenta_id,
                        nombre,
                        monto,
                        fecha if usa_fecha and fecha > date.today() else None
                    )

                    st.success("Meta creada")
                    st.rerun()

                except ValueError as e:

                    st.warning(str(e))

    if not metas:
        st.info("Aún no tienes metas de ahorro.")
        return

    for m in metas:

        with st.container(border=True):

            st.markdown(f"**{m['nombre']}**" + (" ✅" if m["completada"] else ""))

            st.progress(min(m["porcentaje"] / 100, 1.0))

            st.write(
                f"${m['ahorrado']:,.2f} de ${m['monto_objetivo']:,.2f} "
                f"({m['porcentaje']:.0f}%)"
            )

            if not m["completada"]:

                st.caption(f"Te faltan ${m['faltante']:,.2f}")

                if m["ahorro_semanal_sugerido"]:
                    st.caption(
                        f"Para llegar a tiempo ({m['dias_restantes']} días): "
                        f"${m['ahorro_semanal_sugerido']:,.2f} por semana"
                    )

            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                abono = st.number_input(
                    "Monto",
                    min_value=0.0,
                    step=100.0,
                    key=f"abono_{m['id']}",
                    label_visibility="collapsed"
                )

            with c2:
                if st.button("Abonar", key=f"bt_ab_{m['id']}", use_container_width=True):
                    try:
                        ms.abonar(uid, cuenta_id, m["id"], abono)
                        st.rerun()
                    except ValueError as e:
                        st.warning(str(e))

            with c3:
                if st.button("Eliminar", key=f"bt_el_{m['id']}", use_container_width=True):
                    ms.eliminar_meta(cuenta_id, m["id"])
                    st.rerun()
