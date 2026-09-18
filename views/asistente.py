import json
import streamlit as st
from openai import OpenAI

from db import ejecutar_query

AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = st.secrets["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY
)

PROMPT = """
Eres un clasificador financiero.

Devuelve EXCLUSIVAMENTE JSON válido.

Formato:

{
  "tipo":"INGRESO|GASTO",
  "categoria":"",
  "concepto":"",
  "monto":0
}

Categorías válidas:

Gasolina
Comida
Servicios
Transporte
Salud
Entretenimiento
Otros
Ingreso

Ejemplos:

Gasté 350 en gasolina

{
  "tipo":"GASTO",
  "categoria":"Gasolina",
  "concepto":"Gasolina",
  "monto":350
}

Pagué 900 de internet

{
  "tipo":"GASTO",
  "categoria":"Servicios",
  "concepto":"Internet",
  "monto":900
}

Recibí 12000 de salario

{
  "tipo":"INGRESO",
  "categoria":"Ingreso",
  "concepto":"Salario",
  "monto":12000
}

Devuelve solamente JSON.
"""


def interpretar_movimiento(texto):

    st.info("Consultando Azure OpenAI...")

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

    st.success("Azure respondió")

    contenido = response.choices[0].message.content

    st.subheader("Respuesta IA")
    st.code(contenido)

    if contenido.startswith("```json"):
        contenido = contenido.replace("```json", "")
        contenido = contenido.replace("```", "")
        contenido = contenido.strip()

    return json.loads(contenido)


def guardar_movimiento(resultado, texto_original):

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
            :usuario_id,
            :tipo,
            :categoria,
            :concepto,
            :monto,
            :texto_original
        )
        """,
        {
            "usuario_id": st.session_state["user_id"],
            "tipo": resultado["tipo"],
            "categoria": resultado["categoria"],
            "concepto": resultado["concepto"],
            "monto": resultado["monto"],
            "texto_original": texto_original
        }
    )


def pantalla_asistente():

    st.title("🤖 Asistente IA")

    st.write(
        """
Ejemplos:

Gasté 350 en gasolina

Pagué 900 de internet

Comí tacos por 180

Recibí 12000 de salario
"""
    )

    texto = st.text_area(
        "¿Qué pasó?"
    )

    if st.button("Procesar"):

        if not texto.strip():

            st.warning(
                "Escribe una descripción"
            )

            return

        try:

            st.write("Iniciando procesamiento...")

            resultado = interpretar_movimiento(
                texto
            )

            st.write("JSON interpretado:")
            st.json(resultado)

            guardar_movimiento(
                resultado,
                texto
            )

            st.success(
                "✅ Movimiento registrado correctamente"
            )

        except Exception as e:

            st.error(
                f"ERROR: {str(e)}"
            )