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

Debes devolver únicamente JSON válido.

Formato:

{
  "tipo":"INGRESO|GASTO",
  "categoria":"",
  "concepto":"",
  "origen_ingreso":"",
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

Orígenes de ingreso válidos:

Nomina
Honorarios
Comisiones
Venta
Transferencia
Otro

Ejemplos:

Gasté 350 en gasolina

{
  "tipo":"GASTO",
  "categoria":"Gasolina",
  "concepto":"Gasolina",
  "origen_ingreso":"",
  "monto":350
}

Pagué 900 de internet

{
  "tipo":"GASTO",
  "categoria":"Servicios",
  "concepto":"Internet",
  "origen_ingreso":"",
  "monto":900
}

Recibí 12000 de nómina

{
  "tipo":"INGRESO",
  "categoria":"Ingreso",
  "concepto":"Nomina",
  "origen_ingreso":"Nomina",
  "monto":12000
}

Vendí una bicicleta por 3000

{
  "tipo":"INGRESO",
  "categoria":"Ingreso",
  "concepto":"Venta",
  "origen_ingreso":"Venta",
  "monto":3000
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


def guardar_movimiento(
    resultado,
    texto_original
):

    ejecutar_query(
        """
        INSERT INTO gastos.movimientos
        (
            usuario_id,
            tipo,
            categoria,
            concepto,
            monto,
            texto_original,
            origen_ingreso
        )
        VALUES
        (
            :usuario_id,
            :tipo,
            :categoria,
            :concepto,
            :monto,
            :texto_original,
            :origen_ingreso
        )
        """,
        {
            "usuario_id":
                st.session_state["user_id"],

            "tipo":
                resultado["tipo"],

            "categoria":
                resultado["categoria"],

            "concepto":
                resultado["concepto"],

            "monto":
                resultado["monto"],

            "texto_original":
                texto_original,

            "origen_ingreso":
                resultado.get(
                    "origen_ingreso",
                    None
                )
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


def obtener_porcentaje_presupuesto():

    uid = st.session_state["user_id"]

    presupuesto_df = obtener_dataframe(
        f"""
        SELECT monto
        FROM gastos.presupuestos
        WHERE usuario_id = {uid}
        ORDER BY id DESC
        LIMIT 1
        """
    )

    if presupuesto_df.empty:
        return 0

    presupuesto = float(
        presupuesto_df.iloc[0]["monto"]
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

    gastos = float(
        gastos_df.iloc[0]["total"]
    )

    if presupuesto <= 0:
        return 0

    return (gastos / presupuesto) * 100


def pantalla_asistente():

    st.title("🤖 Asistente IA")

    st.markdown(
        """
### Ejemplos

- Gasté 350 en gasolina
- Comí tacos por 180
- Pagué 900 de internet
- Recibí 12000 de nómina
- Vendí una bicicleta por 3000
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

            porcentaje = (
                obtener_porcentaje_presupuesto()
            )

            if resultado["tipo"] == "GASTO":

                mensaje = f"""
✅ Registré un gasto de ${resultado['monto']:,.2f}

📂 Categoría: {resultado['categoria']}

📝 Concepto: {resultado['concepto']}

💰 Disponible actual: ${saldo:,.2f}

📊 Has utilizado {porcentaje:.1f}% de tu presupuesto.
"""

            else:

                mensaje = f"""
✅ Registré un ingreso de ${resultado['monto']:,.2f}

📝 Concepto: {resultado['concepto']}

💰 Disponible actual: ${saldo:,.2f}

📊 Has utilizado {porcentaje:.1f}% de tu presupuesto.
"""

            st.success(
                mensaje
            )

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )