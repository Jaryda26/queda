import streamlit as st
import plotly.express as px
import pandas as pd

from db import obtener_dataframe
from services.insights_service import kpis_periodo, resumen_periodo

CARD = lambda t, v, c: f"""
<div style='background:{c};
padding:18px;
border-radius:12px;
color:white'>
<div>{t}</div>
<div style='font-size:32px;font-weight:bold'>
{v}
</div>
</div>
"""


def pantalla_dashboard():

    cuenta_id = st.session_state["cuenta_id"]

    # TODO el dashboard habla del MISMO periodo que el presupuesto y que
    # la voz: ingresos y gastos del periodo, no del historial completo.
    k = kpis_periodo(cuenta_id)

    ingresos = k["ingresos"]
    gastos = k["gastos"]
    resultado = k["resultado"]
    presupuesto = k["presupuesto"]
    porcentaje = k["porcentaje"]

    st.caption(
        f"📅 Periodo: {k['inicio']:%d/%m/%Y} al {k['fin']:%d/%m/%Y}"
        + (
            f" · {k['dias_restantes']} días restantes"
            if k["dias_restantes"] is not None else " · últimos 30 días"
        )
        + f" · 💼 Saldo acumulado: $ {k['saldo_acumulado']:,.0f}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(
        CARD(
            "Resultado del periodo",
            f"{'+' if resultado >= 0 else '-'}$ {abs(resultado):,.0f}",
            "#2ecc71" if resultado >= 0 else "#e74c3c"
        ),
        unsafe_allow_html=True
    )

    c2.markdown(
        CARD(
            "Ingresos del periodo",
            f"$ {ingresos:,.0f}",
            "#1abc9c"
        ),
        unsafe_allow_html=True
    )

    c3.markdown(
        CARD(
            "Gastos del periodo",
            f"$ {gastos:,.0f}",
            "#3498db"
        ),
        unsafe_allow_html=True
    )

    c4.markdown(
        CARD(
            "Presupuesto de gasto",
            f"$ {presupuesto:,.0f}",
            "#f39c12"
        ),
        unsafe_allow_html=True
    )

    c5.markdown(
        CARD(
            "% Utilizado",
            f"{porcentaje:.1f}%" if presupuesto > 0 else "—",
            "#9b59b6"
        ),
        unsafe_allow_html=True
    )

    st.markdown("---")

    # SEMÁFORO: el presupuesto es un TOPE DE GASTO; el resultado del
    # periodo (ingresos - gastos) es otra cosa y se dice por separado.

    st.markdown("## 🚦 Estado del presupuesto")

    if presupuesto <= 0:

        st.info(
            "Aún no defines un presupuesto. Créalo en 🎯 Presupuesto "
            "(o di: pon mi presupuesto semanal en 2000) para ver aquí "
            "qué tanto de tu tope has usado."
        )

    elif porcentaje < 50:

        st.success(
            f"🟢 Vas muy bien. Has usado {porcentaje:.1f}% de tu "
            "presupuesto y tu ritmo de gasto está controlado."
        )

    elif porcentaje < 80:

        st.warning(
            f"🟡 Atención. Has usado {porcentaje:.1f}% de tu "
            "presupuesto: conviene revisar tus gastos para no exceder "
            "el límite."
        )

    elif porcentaje <= 100:

        st.warning(
            f"🟠 Cerca del tope. Has usado {porcentaje:.1f}% de tu "
            f"presupuesto y te quedan ${max(k['restante'], 0):,.2f}."
        )

    elif resultado >= 0:

        st.warning(
            f"🟠 Te pasaste ${-k['restante']:,.2f} de tu presupuesto de "
            f"gasto ({porcentaje:.1f}%), pero tu periodo va a favor por "
            f"${resultado:,.2f} porque ingresaste ${ingresos:,.2f}. "
            "Cuida el tope en el siguiente periodo."
        )

    else:

        st.error(
            f"🔴 Te pasaste ${-k['restante']:,.2f} de tu presupuesto "
            f"({porcentaje:.1f}%) y además gastaste más de lo que "
            f"ingresaste (-${-resultado:,.2f}). Reduce gastos."
        )

    col1, col2 = st.columns(2)

    with col1:

        graf = pd.DataFrame(
            {
                "Concepto": [
                    "Ingresos",
                    "Gastos",
                    "Resultado"
                ],
                "Monto": [
                    ingresos,
                    gastos,
                    resultado
                ]
            }
        )

        fig = px.bar(
            graf,
            x="Concepto",
            y="Monto",
            title="Ingresos vs Gastos del periodo",
            color="Concepto",
            color_discrete_map={
                "Ingresos": "#1abc9c",
                "Gastos": "#e74c3c",
                "Resultado": "#2ecc71"
            }
        )

        fig.update_layout(
            showlegend=False
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        if k["categorias"]:

            categorias = pd.DataFrame(
                k["categorias"],
                columns=["categoria", "monto"]
            )

            fig2 = px.pie(
                categorias,
                names="categoria",
                values="monto",
                hole=.6,
                title="Gastos del periodo por categoría"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

        else:

            st.info("Aún no hay gastos en este periodo.")

    st.markdown("### Resumen Inteligente")

    try:

        st.info(resumen_periodo(cuenta_id))

    except Exception:

        st.info("Registra movimientos para ver tu resumen del periodo.")

    if presupuesto > 0 and k["restante"] is not None and k["restante"] > 0:

        dias = max(k["dias_restantes"] or 1, 1)

        st.success(
            f"📅 Presupuesto restante: ${k['restante']:,.2f}\n\n"
            f"🎯 Puedes gastar aproximadamente "
            f"${k['restante'] / dias:,.2f} por día durante los "
            f"{dias} días que quedan."
        )

    ultimos = obtener_dataframe(
        """
        SELECT
            fecha,
            categoria,
            concepto,
            tipo,
            monto
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
        ORDER BY fecha DESC
        LIMIT 10
        """,
        {"cuenta_id": cuenta_id}
    )

    st.markdown(
        "### Últimos movimientos"
    )

    st.dataframe(
        ultimos,
        use_container_width=True
    )
