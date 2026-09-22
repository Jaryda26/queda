import random
import streamlit as st

from datetime import date
from datetime import datetime

from db import obtener_dataframe
from db import ejecutar_query

from services.tts_service import texto_a_voz
from datetime import datetime

st.write(
    "DEBUG HORA:",
    datetime.now()
)

st.write(
    "DEBUG HOUR:",
    datetime.now().hour
)
def saludo_hora():

    hora = datetime.now().hour

    if hora < 12:

        return "☀️ Buenos días"

    if hora < 19:

        return "🌤️ Buenas tardes"

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

    porcentaje = 0

    if not presupuesto.empty:

        monto_presupuesto = float(
            presupuesto.iloc[0]["monto"]
        )

        if monto_presupuesto > 0:

            porcentaje = (
                total_gastos /
                monto_presupuesto
            ) * 100

    return disponible, porcentaje


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


def generar_narrativa(
    nombre,
    disponible,
    porcentaje,
    recordatorios
):

    if porcentaje < 50:

        estado = (
            "Vas muy bien. "
            "Tu ritmo de gasto está controlado."
        )

    elif porcentaje < 80:

        estado = (
            "Atención. Ya utilizaste más de la mitad "
            "de tu presupuesto."
        )

    else:

        estado = (
            "Cuidado. Existe riesgo de exceder "
            "tu presupuesto."
        )

    return f"""
Hola {nombre}.

Tu disponible actual es de
{disponible:,.0f} pesos.

Has utilizado
{porcentaje:.1f} por ciento
de tu presupuesto.

Tienes
{recordatorios}
recordatorios pendientes.

{estado}
"""


def pantalla_home():

    uid = st.session_state["user_id"]

    hoy = date.today()

    disponible, porcentaje = (
        obtener_resumen(uid)
    )

    df_recordatorios = obtener_dataframe(
        f"""
        SELECT *
        FROM gastos.recordatorios
        WHERE usuario_id = {uid}
        AND pagado = FALSE
        ORDER BY fecha_vencimiento
        """
    )

    st.title(
        f"{saludo_hora()} {st.session_state['nombre']}"
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

    narrativa = generar_narrativa(
        st.session_state["nombre"],
        disponible,
        porcentaje,
        len(df_recordatorios)
    )

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

    encontrados = 0

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

        encontrados += 1

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

        st.markdown(
            f"""
### {icono} {row['descripcion']}

💰 Monto:
${float(row['monto']):,.2f}

📅 {mensaje}

🔁 Frecuencia:
{row['frecuencia']}
"""
        )

        c1, c2 = st.columns([1, 1])

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