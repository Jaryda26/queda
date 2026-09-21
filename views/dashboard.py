import streamlit as st
import plotly.express as px
import pandas as pd

from db import obtener_dataframe

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

    uid = st.session_state["user_id"]

    ingresos_df = obtener_dataframe(
        f"""
        SELECT
            COALESCE(SUM(monto),0) total
        FROM gastos.movimientos
        WHERE tipo='INGRESO'
        AND usuario_id={uid}
        """
    )

    gastos_df = obtener_dataframe(
        f"""
        SELECT
            COALESCE(SUM(monto),0) total
        FROM gastos.movimientos
        WHERE tipo='GASTO'
        AND usuario_id={uid}
        """
    )

    presupuesto_df = obtener_dataframe(
        f"""
        SELECT monto
        FROM gastos.presupuestos
        WHERE usuario_id={uid}
        ORDER BY id DESC
        LIMIT 1
        """
    )

    ingresos = float(
        ingresos_df.iloc[0]["total"]
    )

    gastos = float(
        gastos_df.iloc[0]["total"]
    )

    presupuesto = (
        float(
            presupuesto_df.iloc[0]["monto"]
        )
        if not presupuesto_df.empty
        else 0
    )

    disponible = ingresos - gastos

    porcentaje = (
        gastos / presupuesto * 100
        if presupuesto > 0
        else 0
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(
        CARD(
            "Disponible",
            f"$ {disponible:,.0f}",
            "#2ecc71"
        ),
        unsafe_allow_html=True
    )

    c2.markdown(
        CARD(
            "Ingresos",
            f"$ {ingresos:,.0f}",
            "#1abc9c"
        ),
        unsafe_allow_html=True
    )

    c3.markdown(
        CARD(
            "Gastos",
            f"$ {gastos:,.0f}",
            "#3498db"
        ),
        unsafe_allow_html=True
    )

    c4.markdown(
        CARD(
            "Presupuesto",
            f"$ {presupuesto:,.0f}",
            "#f39c12"
        ),
        unsafe_allow_html=True
    )

    c5.markdown(
        CARD(
            "% Utilizado",
            f"{porcentaje:.1f}%",
            "#9b59b6"
        ),
        unsafe_allow_html=True
    )

    st.markdown("---")

    # SEMÁFORO INTELIGENTE

    st.markdown("## 🚦 Estado del presupuesto")

    if porcentaje < 50:

        st.success(
            f"""
🟢 Vas muy bien.

Has utilizado {porcentaje:.1f}% de tu presupuesto.

Tu ritmo de gasto está controlado.
"""
        )

    elif porcentaje < 80:

        st.warning(
            f"""
🟡 Atención.

Has utilizado {porcentaje:.1f}% de tu presupuesto.

Conviene revisar tus gastos para no exceder el límite.
"""
        )

    else:

        st.error(
            f"""
🔴 Riesgo de exceder el presupuesto.

Has utilizado {porcentaje:.1f}% de tu presupuesto.

Reduce gastos para evitar terminar el periodo sin saldo.
"""
        )

    col1, col2 = st.columns(2)

    with col1:

        graf = pd.DataFrame(
            {
                "Concepto": [
                    "Ingresos",
                    "Gastos",
                    "Disponible"
                ],
                "Monto": [
                    ingresos,
                    gastos,
                    disponible
                ]
            }
        )

        fig = px.bar(
            graf,
            x="Concepto",
            y="Monto",
            title="Ingresos vs Gastos vs Disponible",
            color="Concepto",
            color_discrete_map={
                "Ingresos": "#1abc9c",
                "Gastos": "#e74c3c",
                "Disponible": "#2ecc71"
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

        categorias = obtener_dataframe(
            f"""
            SELECT
                COALESCE(
                    categoria,
                    'Sin categoría'
                ) categoria,
                SUM(monto) monto
            FROM gastos.movimientos
            WHERE tipo='GASTO'
            AND usuario_id={uid}
            GROUP BY categoria
            """
        )

        if not categorias.empty:

            fig2 = px.pie(
                categorias,
                names="categoria",
                values="monto",
                hole=.6,
                title="Gastos por Categoría"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

    st.markdown("### Resumen Inteligente")

    st.info(
        f"""
💰 Disponible actual:
${disponible:,.2f}

📊 Has utilizado
{porcentaje:.1f}% de tu presupuesto.
"""
    )

    dias_periodo = 30

    if presupuesto > 0:

        restante = presupuesto - gastos

        gasto_diario = (
            restante / dias_periodo
        )

        st.success(
            f"""
📅 Presupuesto restante:
${restante:,.2f}

🎯 Puedes gastar aproximadamente

${gasto_diario:,.2f}
por día.
"""
        )

    top_categoria = obtener_dataframe(
        f"""
        SELECT
            categoria,
            SUM(monto) total
        FROM gastos.movimientos
        WHERE tipo='GASTO'
        AND usuario_id={uid}
        GROUP BY categoria
        ORDER BY total DESC
        LIMIT 1
        """
    )

    if not top_categoria.empty:

        st.warning(
            f"""
📂 Categoría con mayor gasto:

{top_categoria.iloc[0]['categoria']}

💸 Total:
${top_categoria.iloc[0]['total']:,.2f}
"""
        )

    ultimos = obtener_dataframe(
        f"""
        SELECT
            fecha,
            categoria,
            concepto,
            tipo,
            monto
        FROM gastos.movimientos
        WHERE usuario_id={uid}
        ORDER BY fecha DESC
        LIMIT 10
        """
    )

    st.markdown(
        "### Últimos movimientos"
    )

    st.dataframe(
        ultimos,
        use_container_width=True
    )