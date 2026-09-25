import random
import streamlit as st

from datetime import date


from db import obtener_dataframe
from db import ejecutar_query

from services.tts_service import texto_a_voz
from services.recordatorios_service import marcar_pagado
from services.narrativa_service import (
    generar_narrativa_ia,
    calcular_datos_proyeccion,
    escapar_para_markdown
)
from services.billing_service import obtener_plan_actual

from datetime import datetime
from zoneinfo import ZoneInfo

ahora = datetime.now(
    ZoneInfo("America/Mexico_City")
)

def saludo_hora():

    ahora = datetime.now(
        ZoneInfo("America/Mexico_City"
        )
    )
    hora = ahora.hour

    if hora < 12:

        return "☀️ Buenos días"

    elif hora < 19:

        return "🌤️ Buenas tardes"

    else:

        return "🌙 Buenas noches"

def registrar_pago(uid, cuenta_id, descripcion, monto):

    ejecutar_query(
        """
        INSERT INTO gastos.movimientos
        (
            usuario_id,
            cuenta_id,
            tipo,
            categoria,
            concepto,
            monto,
            texto_original
        )
        VALUES
        (
            :uid,
            :cuenta_id,
            'GASTO',
            'Recordatorio',
            :concepto,
            :monto,
            :texto
        )
        """,
        {
            "uid": uid,
            "cuenta_id": cuenta_id,
            "concepto": descripcion,
            "monto": monto,
            "texto": f"Pago automático de {descripcion}"
        }
    )


def frase_del_dia():

    frases = [

        "💰 Cada peso registrado te acerca a una mejor decisión.",

        "📈 Lo que no se mide no se puede mejorar.",

        "🎯 Hoy es un buen día para revisar tus gastos.",

        "🚦 Mantén el control de tus finanzas.",

        "💳 Atiende tus compromisos antes del vencimiento.",

        "🧠 El hábito financiero vale más que cualquier herramienta."
    ]

    return random.choice(frases)


def pantalla_home():

    uid = st.session_state["user_id"]
    cuenta_id = st.session_state["cuenta_id"]

    hoy = date.today()

    df_recordatorios = obtener_dataframe(
        """
        SELECT *
        FROM gastos.recordatorios
        WHERE cuenta_id = :cuenta_id
        AND pagado = FALSE
        ORDER BY fecha_vencimiento
        """,
        {"cuenta_id": cuenta_id}
    )

    nombre = st.session_state["nombre_corto"].split()[0]

    st.title(
        f"{saludo_hora()} {nombre}"
    )

    if st.session_state.get(
        "ultimo_texto_voz"
    ):

        st.caption(
            f"🎤 Último comando: "
            f"{st.session_state['ultimo_texto_voz']}"
        )
    st.info(
        frase_del_dia()
    )

    plan = obtener_plan_actual(cuenta_id)

    usar_ia = bool(
        plan is not None
        and plan.get("incluye_ia", True)
    )

    datos_proyeccion = calcular_datos_proyeccion(cuenta_id)

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "💰 Disponible",
            f"${datos_proyeccion['disponible_actual']:,.0f}"
        )

    with col2:

        proyeccion = datos_proyeccion["proyeccion_fin_periodo"]

        st.metric(
            "📈 Proyección del periodo",
            (
                f"${proyeccion:,.0f}"
                if proyeccion is not None
                else "—"
            ),
            delta=(
                "Margen" if (
                    proyeccion is not None and proyeccion >= 0
                )
                else "Déficit" if proyeccion is not None
                else None
            ),
            delta_color=(
                "normal" if (
                    proyeccion is None or proyeccion >= 0
                )
                else "inverse"
            )
        )

    with col3:

        st.metric(
            "🔔 Recordatorios pendientes",
            len(df_recordatorios)
        )

    narrativa = generar_narrativa_ia(
        cuenta_id,
        usar_ia=usar_ia,
        datos=datos_proyeccion
    )

    st.success(escapar_para_markdown(narrativa))

    # ====================================
    # VOZ DE BIENVENIDA
    # ====================================

    if "saludo_reproducido" not in st.session_state:

        try:

            # OJO: texto_a_voz() recibe "narrativa" SIN escapar.
            # Si le pasamos la versión con \$ (la del st.success de
            # arriba), Azure Speech lee la barra invertida en voz
            # alta ("barra invertida") y rompe el audio justo antes
            # de cada monto — pasó en producción, quedó documentado
            # en narrativa_service.escapar_para_markdown().

            archivo_audio = texto_a_voz(
                narrativa
            )

            st.audio(
                archivo_audio,
                format="audio/wav",
                autoplay=True
            )

            st.session_state[
                "saludo_reproducido"
            ] = True

        except Exception:
            pass

    st.markdown("---")

    # ====================================
    # PREPARAR TARJETAS DE RECORDATORIOS
    # ====================================

    tarjetas = []

    for _, row in df_recordatorios.iterrows():

        if row["fecha_vencimiento"] is None:
            continue

        fecha_vencimiento = (
            row["fecha_vencimiento"]
        )

        dias_restantes = (
            fecha_vencimiento - hoy
        ).days

        # Si está vencido también se muestra

        if dias_restantes > int(
            row["dias_anticipacion"]
        ):
            continue

        if dias_restantes < 0:

            icono = "🔴"

            mensaje = (
                f"Venció hace "
                f"{abs(dias_restantes)} día(s)"
            )

        elif dias_restantes <= 1:

            icono = "🔴"

            mensaje = (
                "Vence hoy o mañana"
            )

        elif dias_restantes <= 3:

            icono = "🟡"

            mensaje = (
                f"Vence en "
                f"{dias_restantes} día(s)"
            )

        else:

            icono = "🔔"

            mensaje = (
                f"Vence en "
                f"{dias_restantes} día(s)"
            )

        tarjetas.append(
            {
                "row": row,
                "icono": icono,
                "mensaje": mensaje,
            }
        )

    encontrados = len(tarjetas)

    # ====================================
    # RENDERIZAR TARJETAS EN HORIZONTAL
    # ====================================

    TARJETAS_POR_FILA = 3

    for i in range(0, len(tarjetas), TARJETAS_POR_FILA):

        fila = tarjetas[i:i + TARJETAS_POR_FILA]
        columnas = st.columns(len(fila))

        for col, tarjeta in zip(columnas, fila):

            row = tarjeta["row"]
            icono = tarjeta["icono"]
            mensaje = tarjeta["mensaje"]

            with col:

                with st.container(border=True):

                    st.markdown(
                        f"**{icono} {row['descripcion']}**"
                    )

                    st.markdown(
                        f"💰 ${float(row['monto']):,.2f}"
                    )

                    st.caption(f"📅 {mensaje}")
                    st.caption(
                        f"🔁 {row['frecuencia']}"
                    )

                    b1, b2 = st.columns([1, 1])

                    with b1:

                        if st.button(
                            "✅ Pagado",
                            key=f"pagado_{row['id']}",
                            use_container_width=True
                        ):

                            registrar_pago(
                                uid,
                                cuenta_id,
                                row["descripcion"],
                                float(row["monto"])
                            )

                            marcar_pagado(
                                int(row["id"]),
                                row["fecha_vencimiento"],
                                row["frecuencia"]
                            )

                            st.success(
                                "✅ Pago registrado"
                            )

                            st.rerun()

                    with b2:

                        if st.button(
                            "⏰ Después",
                            key=f"despues_{row['id']}",
                            use_container_width=True
                        ):

                            ejecutar_query(
                                """
                                UPDATE gastos.recordatorios
                                SET
                                    fecha_proxima_alerta =
                                    CURRENT_DATE + INTERVAL '1 day'
                                WHERE id = :id
                                """,
                                {
                                    "id":
                                        int(row["id"])
                                }
                            )

                            st.success(
                                "⏰ Te lo recordaré mañana"
                            )

                            st.rerun()

    if encontrados == 0:

        st.success(
            "✅ No tienes recordatorios pendientes."
        )

    if st.button("Entendido"):

        st.session_state[
            "pagina_actual"
        ] = "Dashboard"

        st.rerun()