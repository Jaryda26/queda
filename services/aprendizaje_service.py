from db import obtener_dataframe
from services.intent_engine import normalizar_texto, extraer_monto_de_texto


def _frase_coincide(frase_normalizada, texto_normalizado):
    """
    Compara por PALABRAS EN ORDEN, no como texto pegado — así
    "ya cayó la beca" sigue reconociendo "ya ME cayó la beca,
    5000 pesos" aunque se haya insertado una palabra en medio.
    Exigir el texto exacto era demasiado frágil: nadie repite una
    frase enseñada palabra por palabra idéntica cada vez.
    """

    palabras_frase = frase_normalizada.split()
    palabras_texto = texto_normalizado.split()

    if not palabras_frase:
        return False

    i = 0

    for palabra in palabras_texto:

        if palabra == palabras_frase[i]:

            i += 1

            if i == len(palabras_frase):
                return True

    return False


def buscar_frase_aprendida(cuenta_id, texto):
    """
    Revisa si el texto contiene alguna frase que el usuario enseñó
    en 🧠 Aprendizaje, y si sí, arma el mismo tipo de "resultado"
    que produce el motor de reglas (detectar_intencion) o la IA,
    para que se procese exactamente igual en ejecutar_accion().

    Antes de esto, las frases guardadas en Aprendizaje NUNCA se
    consultaban en ningún lado del reconocimiento — se podían
    guardar, pero no hacían nada. Esta es la pieza que faltaba.

    Regresa None si no hay ninguna coincidencia (así el texto
    sigue su camino normal: reglas de fábrica, y si tampoco
    matchea nada ahí, la IA).
    """

    df = obtener_dataframe(
        """
        SELECT frase, accion, categoria
        FROM gastos.diccionario_usuario
        WHERE cuenta_id = :cuenta_id
        """,
        {"cuenta_id": cuenta_id}
    )

    if df.empty:
        return None

    texto_normalizado = normalizar_texto(texto)

    for _, fila in df.iterrows():

        frase_normalizada = normalizar_texto(
            str(fila["frase"])
        )

        if (
            not frase_normalizada
            or not _frase_coincide(
                frase_normalizada,
                texto_normalizado
            )
        ):
            continue

        accion = str(fila["accion"]).upper()

        categoria = fila["categoria"]

        categoria = (
            str(categoria).strip()
            if categoria and str(categoria).strip()
            else None
        )

        if accion == "REGISTRAR_INGRESO":

            monto = extraer_monto_de_texto(texto)

            if monto is not None:

                return {
                    "accion": "REGISTRAR_INGRESO",
                    "concepto": categoria or "Ingreso",
                    "origen_ingreso": categoria or "Ingreso",
                    "monto": monto
                }

            # Igual que las frases de fábrica ("ya cayó el
            # águila"): si no dijeron el monto en la misma frase,
            # se pregunta y se espera la respuesta.

            return {"accion": "PREGUNTAR_MONTO_INGRESO"}

        if accion == "REGISTRAR_GASTO":

            monto = extraer_monto_de_texto(texto)

            return {
                "accion": "REGISTRAR_GASTO",
                "categoria": categoria or "Otros",
                "concepto": categoria or "Gasto",
                "monto": monto or 0
            }

        if accion in ("PAGAR_RECORDATORIO", "POSPONER_RECORDATORIO"):

            return {
                "accion": accion,
                "descripcion": categoria or str(fila["frase"])
            }

    return None
