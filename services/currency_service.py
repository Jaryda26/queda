import requests


def obtener_tipo_cambio_usd_mxn():
    """
    Tipo de cambio USD -> MXN del día, de la API de acceso abierto
    de ExchangeRate-API (open.er-api.com) — no requiere llave, pero
    se actualiza solo una vez al día (no es minuto a minuto).

    Atribución requerida por sus términos: datos de
    https://www.exchangerate-api.com

    Regresa un dict {"valor": float, "fecha_actualizacion": str}
    o None si la consulta falla por cualquier motivo — nunca debe
    tronar el resto de la conversación por esto.
    """

    try:

        respuesta = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5
        )

        datos = respuesta.json()

        if datos.get("result") != "success":
            return None

        return {
            "valor": float(datos["rates"]["MXN"]),
            "fecha_actualizacion": datos.get(
                "time_last_update_utc",
                ""
            )
        }

    except Exception:
        return None
