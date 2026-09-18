import json
import streamlit as st

from openai import OpenAI

from db import ejecutar_query
from db import obtener_dataframe

AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = st.secrets["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY
)

PROMPT = """
Eres un asistente financiero.

Analiza el texto del usuario.

Devuelve EXCLUSIVAMENTE JSON válido.

Formato:

{
  "tipo":"INGRESO|GASTO",
  "categoria":"",
  "concepto":"",
  "monto":0
}

Categorias válidas:

Gasolina
Comida
Servicios
Transporte
Salud
Entretenimiento
Otros
Ingreso

Reglas:

- gasolina, diesel, combustible => Gasolina
- tacos, comida, restaurante, cena => Comida
- uber, taxi, transporte => Transporte
- internet, luz, agua => Servicios
- hospital, medico, farmacia => Salud
- netflix, cine => Entretenimiento
- sueldo, salario, nomina => Ingreso

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
            )

            AS saldo

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

- Gasté 350 en gasolina
- Comí tacos por 180
- Pagué 900 de internet
- Recibí 12000 de salario
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

            resultado = interpretar_movimiento(
                texto
            )

            guardar_movimiento(
                resultado,
                texto
            )

            saldo = obtener_saldo()

            if resultado["tipo"] == "GASTO":

                mensaje = f"""
✅ Registré un gasto de ${resultado['monto']:,.2f}

📂 Categoría: {resultado['categoria']}

📝 Concepto: {resultado['concepto']}

💰 Disponible actual: ${saldo:,.2f}
"""

            else:

                mensaje = f"""
✅ Registré un ingreso de ${resultado['monto']:,.2f}

📝 Concepto: {resultado['concepto']}

💰 Disponible actual: ${saldo:,.2f}
"""

            st.success(mensaje)

            with st.expander(
                "Ver detalle IA"
            ):
                st.json(resultado)

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )