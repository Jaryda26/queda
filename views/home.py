import streamlit as st
from datetime import date
import random

from db import obtener_dataframe
from db import ejecutar_query


def registrar_pago(uid, descripcion, monto):

    ejecutar_query(
        """
        INSERT INTO gastos.movimientos
        (
            usuario_id,
            tipo,
            categoria,
            concepto,
            monto,
            texto_original
        )
        VALUES
        (
            :uid,
            'GASTO',
            'Recordatorio',
            :concepto,
            :monto,
            :texto
        )
        """,
        {
            "uid": uid,
            "concepto": descripcion,
            "monto": monto,
            "texto": f"Pago automático de {descripcion}"
        }
    )


def obtener_resumen(uid):

    ingresos = obtener_dataframe(
        f"""
        SELECT
            COALESCE(SUM(monto),0) total
        FROM gastos.movimientos
        WHERE tipo='INGRESO'
        AND usuario_id={uid}
        """
    )

    gastos = obtener_dataframe(
        f"""
        SELECT
            COALESCE(SUM(monto),0) total
        FROM gastos.movimientos
        WHERE tipo='GASTO'
        AND usuario_id={uid}
        """
    )

    presupuesto = obtener_dataframe(
        f"""
        SELECT monto
        FROM gastos.presupuestos
        WHERE usuario_id={uid}
        ORDER BY id DESC
        LIMIT 1
        """
    )

    total_ingresos = float(
        ingresos.iloc[0]["total"]
    )

    total_gastos = float(
        gastos.iloc[0]["total"]
    )

    disponible = (
        total_ingresos - total_gastos
    )

    if presupuesto.empty:

        porcentaje = 0

    else:

        monto_presupuesto = float(
            presupuesto.iloc[0]["monto"]
        )

        porcentaje = (
            total_gastos /
            monto_presupuesto * 100
        ) if monto_presupuesto > 0 else 0

    return disponible, porcentaje


def saludo_financiero(
    disponible,
    porcentaje
):

    if porcentaje < 50:

        return (
            "🟢 Vas muy bien.\n\n"
            "Tu ritmo de gasto está controlado."
        )

    if porcentaje < 80:

        return (
            "🟡 Atención.\n\n"
            "Ya utilizaste más de la mitad "
            "de tu presupuesto."
        )

    return (
        "🔴 Cuidado.\n\n"
        "Existe riesgo de exceder "
        "tu presupuesto."
    )


def frase_del_dia():

    frases = [

        "💰 Cada peso registrado te acerca a una mejor decisión.",

        "📈 Lo que no se mide no se puede mejorar.",

        "🎯 Hoy es un buen día para revisar tus gastos.",

        "🚦 Mantén el control de tus finanzas.",

        "💳 Atiende tus compromisos antes de que se conviertan en problemas.",

        "🧠 El hábito financiero vale más que cualquier herramienta."
    ]

    hoy = date.today().day

    return frases[
        hoy % len(frases)
    ]


def pantalla_home():

    uid = st.session_state["user_id"]

    hoy = date.today()

    disponible, porcentaje = (
        obtener_resumen(uid)
    )

    st.title(
        f"🔔 Buenos días {st.session_state['nombre']}"
    )

    st.info(
        frase_del_dia()
    )

    st.success(
        f"""
💰 Disponible actual:
${disponible:,.2f}

📊 Presupuesto utilizado:
{porcentaje:.1f}%
"""
    )

    st.warning(
        saludo_financiero(
            disponible,
            porcentaje
        )
    )

    st.markdown("---")

    df = obtener_dataframe(
        f"""
        SELECT
            id,
            descripcion,
            monto,
            dia_vencimiento,
            dias_anticipacion,
            frecuencia,
            pagado
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        AND pagado = FALSE
        ORDER BY dia_vencimiento
        """
    )

    encontrados = 0

    for _, row in df.iterrows():

        dias_restantes = (
            int(row["dia_vencimiento"])
            - hoy.day
        )

        if dias_restantes < 0:

            dias_restantes += 30

        if dias_restantes > int(
            row["dias_anticipacion"]
        ):
            continue

        encontrados += 1

        icono = "🔔"

        if dias_restantes <= 1:

            icono = "🔴"

        elif dias_restantes <= 3:

            icono = "🟡"

        st.markdown(
            f"""
### {icono} {row['descripcion']}

💰 Monto:
${float(row['monto']):,.2f}

📅 Vence en:
{dias_restantes} día(s)

🔁 Frecuencia:
{row['frecuencia']}
"""
        )

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "✅ Pagado",
                key=f"pagado_{row['id']}"
            ):

                registrar_pago(
                    uid,
                    row["descripcion"],
                    float(row["monto"])
                )

                if (
                    str(
                        row["frecuencia"]
                    ).upper()
                    == "UNICO"
                ):

                    ejecutar_query(
                        """
                        UPDATE gastos.recordatorios
                        SET
                            pagado = TRUE,
                            fecha_ultimo_pago =
                            CURRENT_DATE
                        WHERE id = :id
                        """,
                        {
                            "id":
                                int(row["id"])
                        }
                    )

                else:

                    ejecutar_query(
                        """
                        UPDATE gastos.recordatorios
                        SET
                            fecha_ultimo_pago =
                            CURRENT_DATE
                        WHERE id = :id
                        """,
                        {
                            "id":
                                int(row["id"])
                        }
                    )

                st.success(
                    "✅ Pago registrado"
                )

                st.rerun()

        with c2:

            if st.button(
                "⏰ Después",
                key=f"despues_{row['id']}"
            ):

                st.info(
                    "Te lo recordaré más tarde."
                )

        st.divider()

    if encontrados == 0:

        st.success(
            "✅ No tienes recordatorios pendientes."
        )

    if st.button("Entendido"):

        st.session_state[
            "pagina_actual"
        ] = "Dashboard"

        st.rerun()