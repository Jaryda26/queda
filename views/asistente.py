import json
from datetime import date
import streamlit as st

from db import obtener_dataframe

from services.intent_engine import detectar_intencion
from services.action_engine import ejecutar_accion
from services.ai_client import get_openai_client, get_deployment
from services.billing_service import obtener_plan_actual


PROMPT_BASE = """
Eres el motor financiero de Queda.

Devuelve únicamente JSON válido.

Acciones válidas:

REGISTRAR_GASTO
REGISTRAR_INGRESO
CREAR_RECORDATORIO
PAGAR_RECORDATORIO
POSPONER_RECORDATORIO
ABRIR_DASHBOARD
ABRIR_RECORDATORIOS
ABRIR_CUENTA
ABRIR_SUSCRIPCION

Ejemplos:

Compré una coca de 25 pesos

{
  "accion":"REGISTRAR_GASTO",
  "categoria":"Comida",
  "concepto":"Coca",
  "monto":25
}

Gasté 350 en gasolina

{
  "accion":"REGISTRAR_GASTO",
  "categoria":"Gasolina",
  "concepto":"Gasolina",
  "monto":350
}

Ayer compré café en Starbucks, 200 pesos

{
  "accion":"REGISTRAR_GASTO",
  "categoria":"Comida",
  "concepto":"Café Starbucks",
  "monto":200,
  "fecha":"<resuelve 'ayer' a una fecha YYYY-MM-DD usando la fecha de hoy que te doy abajo>"
}

Antier gasté 500 en el súper

{
  "accion":"REGISTRAR_GASTO",
  "categoria":"Otros",
  "concepto":"Súper",
  "monto":500,
  "fecha":"<resuelve 'antier' (hace 2 días) a YYYY-MM-DD>"
}

Me depositaron 12000 de nómina

{
  "accion":"REGISTRAR_INGRESO",
  "concepto":"Nomina",
  "origen_ingreso":"Nomina",
  "monto":12000
}

Pago de nómina 12000

{
  "accion":"REGISTRAR_INGRESO",
  "concepto":"Nomina",
  "origen_ingreso":"Nomina",
  "monto":12000
}

Ya pagué Sears

{
  "accion":"PAGAR_RECORDATORIO",
  "descripcion":"SEARS"
}

Después Sears

{
  "accion":"POSPONER_RECORDATORIO",
  "descripcion":"SEARS"
}

Muéstrame estadísticas

{
  "accion":"ABRIR_DASHBOARD"
}

Qué tengo pendiente

{
  "accion":"ABRIR_RECORDATORIOS"
}

Abre mi cuenta

{
  "accion":"ABRIR_CUENTA"
}

Muéstrame mi plan

{
  "accion":"ABRIR_SUSCRIPCION"
}

Recuérdame pagar la tarjeta Sears el próximo viernes por 1300 pesos

{
  "accion":"CREAR_RECORDATORIO",
  "descripcion":"Tarjeta Sears",
  "monto":1300,
  "fecha_vencimiento":"<resuelve 'próximo viernes' a una fecha YYYY-MM-DD usando la fecha de hoy que te doy abajo>",
  "frecuencia":"UNICO",
  "dias_anticipacion":3
}

Ponme un recordatorio mensual de la renta, 3500 pesos, cada día 5

{
  "accion":"CREAR_RECORDATORIO",
  "descripcion":"Renta",
  "monto":3500,
  "fecha_vencimiento":"<el día 5 más próximo desde hoy, YYYY-MM-DD>",
  "frecuencia":"MENSUAL",
  "dias_anticipacion":3
}

Reglas para REGISTRAR_GASTO y REGISTRAR_INGRESO:
- "fecha" es OPCIONAL: solo inclúyela si el usuario menciona
  explícitamente cuándo pasó ("ayer", "antier", "el lunes", "el 20
  de septiembre"). Si no dice nada, NO incluyas el campo "fecha"
  (se registra con la fecha/hora de hoy automáticamente).
- Cuando sí incluyas "fecha", SIEMPRE en formato YYYY-MM-DD,
  resuelta a partir de la fecha de hoy que se te da al final de
  este mensaje — nunca la dejes como texto libre.

Reglas para CREAR_RECORDATORIO:
- "fecha_vencimiento" SIEMPRE en formato YYYY-MM-DD, resuelta a
  partir de la fecha de hoy que se te da al final de este mensaje
  — nunca la dejes como texto libre ("el viernes"), conviértela.
- "frecuencia" debe ser una de: UNICO, SEMANAL, QUINCENAL, MENSUAL,
  ANUAL. Si no se especifica, usa UNICO.
- "dias_anticipacion" es un entero (días antes para avisar); si no
  se especifica, usa 3.
- Si no puedes identificar con confianza la fecha o el monto, deja
  ese campo como null en vez de inventar un valor.

Devuelve únicamente JSON.
"""


def _prompt_con_fecha():

    hoy = date.today()

    dias_semana = [
        "lunes", "martes", "miércoles", "jueves",
        "viernes", "sábado", "domingo"
    ]

    contexto_fecha = (
        f"\nHoy es {dias_semana[hoy.weekday()]}, "
        f"{hoy.isoformat()}. Usa esta fecha como referencia para "
        f"resolver cualquier fecha relativa (\"el viernes\", "
        f"\"en 3 días\", \"el próximo mes\", etc.).\n"
    )

    return PROMPT_BASE + contexto_fecha


def interpretar_movimiento(texto):

    client = get_openai_client()
    deployment = get_deployment()

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": _prompt_con_fecha()
            },
            {
                "role": "user",
                "content": texto
            }
        ],
        temperature=0
    )

    contenido = response.choices[0].message.content

    if contenido.startswith("```json"):

        contenido = contenido.replace(
            "```json",
            ""
        )

        contenido = contenido.replace(
            "```",
            ""
        )

        contenido = contenido.strip()

    return json.loads(contenido)


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

            intencion = detectar_intencion(
                texto
            )

            if intencion and intencion["accion"] in [
                "ABRIR_DASHBOARD",
                "ABRIR_RECORDATORIOS",
                "PAGAR_RECORDATORIO",
                "POSPONER_RECORDATORIO",
                "PREGUNTAR_MONTO_INGRESO"
            ]:

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