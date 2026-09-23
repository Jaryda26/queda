import random
import streamlit as st

from datetime import date


from db import obtener_dataframe
from db import ejecutar_query

from services.tts_service import texto_a_voz
from services.recordatorios_service import marcar_pagado
from services.narrativa_service import generar_narrativa_ia

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

    hoy = date.today()

    df_recordatorios = obtener_dataframe(
        """
        SELECT *
        FROM gastos.recordatorios
        WHERE usuario_id = :uid
        AND pagado = FALSE
        ORDER BY fecha_vencimiento
        """,
        {"uid": uid}
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

    narrativa = generar_narrativa_ia(uid)

    st.success(narrativa)

    # ====================================
    # VOZ DE BIENVENIDA
    # ====================================

    if "saludo_reproducido" not in st.session_state:

        try:

            archivo_audio = texto_a_voz(
                narrativa
            )

            st.audio(
                archivo_audio
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