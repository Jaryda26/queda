import json
from datetime import date
import streamlit as st

from db import obtener_dataframe

from services.intent_engine import detectar_intencion
from services.aprendizaje_service import buscar_frase_aprendida
from services.action_engine import ejecutar_accion
from services.ai_client import get_openai_client, get_deployment
from services.billing_service import obtener_plan_actual


from services.interprete_ia import (
    PROMPT_BASE,
    _prompt_con_fecha,
    interpretar_movimiento
)

def obtener_saldo():

    df = obtener_dataframe(
        """
        SELECT

            COALESCE(
                SUM(
                    CASE
                        WHEN tipo='INGRESO'
                        THEN monto
                        ELSE 0
                    END
                ),
                0
            )

            -

            COALESCE(
                SUM(
                    CASE
                        WHEN tipo='GASTO'
                        THEN monto
                        ELSE 0
                    END
                ),
                0
            ) AS saldo

        FROM gastos.movimientos

        WHERE cuenta_id = :cuenta_id
        """,
        {"cuenta_id": st.session_state["cuenta_id"]}
    )

    return float(
        df.iloc[0]["saldo"]
    )


def pantalla_asistente():

    st.title("🤖 Asistente IA")

    plan = obtener_plan_actual(
        st.session_state["cuenta_id"]
    )

    if plan is None or not plan.get("incluye_ia", True):

        st.warning(
            "🔒 El Asistente IA está disponible desde el plan "
            "Individual. Sube de plan en 💳 Suscripción para "
            "desbloquearlo."
        )

        return

    st.markdown(
        """
### Ejemplos

- Compré una coca de 25 pesos
- Gasté 350 en gasolina
- Ya cayó el águila
- Ya chilló la marrana
- Pago de nómina
- Ya pagué Sears
- Después Sears
- Muéstrame estadísticas
- Recuérdame pagar la tarjeta Sears el próximo viernes por 1300
- Ponme un recordatorio mensual de la renta, 3500, cada día 5
- Tengo que tramitar mi tarjeta de residente en Tepo en septiembre de 2027
- Quedé de comprarle un pastel a mi hija, acuérdame hoy es su cumpleaños
- Repite el resumen
- Dame algún consejo
- Hoy a cómo está el dólar, ¿valdrá la pena ahorrar?
- Si ahorro 100 pesos a la semana, ¿cuánto junto al fin de año?
"""
    )

    texto = st.text_area(
        "¿Qué pasó?"
    )

    # ===================================================
    # ESPERANDO MONTO DE INGRESO
    # ===================================================

    if st.session_state.get(
        "esperando_monto_ingreso",
        False
    ):

        if st.button("Procesar"):

            try:

                monto = float(texto)

                resultado = {
                    "accion": "REGISTRAR_INGRESO",
                    "concepto": "Ingreso",
                    "origen_ingreso": "Ingreso",
                    "monto": monto,
                    "texto_original": texto
                }

                mensaje = ejecutar_accion(
                    resultado
                )

                st.session_state[
                    "esperando_monto_ingreso"
                ] = False

                st.success(
                    mensaje
                )

                try:

                    saldo = obtener_saldo()

                    st.info(
                        f"""
💰 Disponible actual

${saldo:,.2f}
"""
                    )

                except Exception:
                    pass

            except Exception:

                st.warning(
                    "Indica solamente el monto."
                )

        return

    # ===================================================
    # FLUJO NORMAL
    # ===================================================

    if st.button("Procesar"):

        if not texto.strip():

            st.warning(
                "Escribe una descripción."
            )

            return

        try:

            intencion = buscar_frase_aprendida(
                st.session_state["cuenta_id"],
                texto
            )

            if intencion is None:

                intencion = detectar_intencion(
                    texto
                )

            if intencion:

                mensaje = ejecutar_accion(
                    intencion
                )

                st.success(
                    mensaje
                )

                return

            resultado = interpretar_movimiento(
                texto
            )

            resultado["texto_original"] = texto

            mensaje = ejecutar_accion(
                resultado
            )

            st.success(
                mensaje
            )

            try:

                saldo = obtener_saldo()

                st.info(
                    f"""
💰 Disponible actual

${saldo:,.2f}
"""
                )

            except Exception:
                pass

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )