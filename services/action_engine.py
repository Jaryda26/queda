import json
import streamlit as st

from openai import OpenAI

from db import ejecutar_query
from db import obtener_dataframe

from services.intent_engine import detectar_intencion


AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = st.secrets["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY
)

PROMPT = """
Eres el motor financiero de Queda.

Devuelve únicamente JSON válido.

Acciones válidas:

REGISTRAR_GASTO
REGISTRAR_INGRESO
PAGAR_RECORDATORIO
POSPONER_RECORDATORIO
ABRIR_DASHBOARD
ABRIR_RECORDATORIOS

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

Devuelve únicamente JSON.
"""


def interpretar_movimiento(texto):

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": PROMPT
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
        f"""
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
            ) saldo

        FROM gastos.movimientos

        WHERE usuario_id =
        {st.session_state["user_id"]}
        """
    )

    return float(
        df.iloc[0]["saldo"]
    )


def pantalla_asistente():

    st.title("🤖 Asistente IA")

    st.markdown(
        """
### Ejemplos

- Compré una coca de 25 pesos
- Gasté 350 en gasolina
- Ya cayó el águila
- Pago de nómina
- Ya pagué Sears
- Después Sears
- Muéstrame estadísticas
"""
    )

    texto = st.text_area(
        "¿Qué pasó?"
    )

    # =====================================================
    # ESPERANDO MONTO DE INGRESO
    # =====================================================

    if st.session_state.get(
        "esperando_monto_ingreso",
        False
    ):

        if st.button("Procesar"):

            try:

                monto = float(texto)

                resultado = {
                    "accion":
                        "REGISTRAR_INGRESO",

                    "concepto":
                        "Ingreso",

                    "origen_ingreso":
                        "Ingreso",

                    "monto":
                        monto,

                    "texto_original":
                        texto
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

            except Exception:

                st.warning(
                    "Indica solamente el monto."
                )

        return

    # =====================================================
    # FLUJO NORMAL
    # =====================================================

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

            if intencion:

                if (
                    intencion["accion"]
                    in
                    [
                        "ABRIR_DASHBOARD",
                        "ABRIR_RECORDATORIOS",
                        "PAGAR_RECORDATORIO",
                        "POSPONER_RECORDATORIO",
                        "PREGUNTAR_MONTO_INGRESO"
                    ]
                ):

                    mensaje = ejecutar_accion(
                        intencion
                    )

                    st.success(
                        mensaje
                    )

                    return

                else:

                    resultado = interpretar_movimiento(
                        texto
                    )

                    resultado["accion"] = (
                        intencion["accion"]
                    )

            else:

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

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )