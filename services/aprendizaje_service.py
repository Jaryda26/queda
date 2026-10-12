from db import ejecutar_query, obtener_dataframe
from services.intent_engine import (
    normalizar_texto,
    extraer_monto_de_texto,
    detectar_ensenanza,
)

ACCIONES_VALIDAS = (
    "REGISTRAR_GASTO",
    "REGISTRAR_INGRESO",
    "PAGAR_RECORDATORIO",
    "TERMINAR_ACTIVIDAD",
    "POSPONER_RECORDATORIO",
)


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

    # "aprende que X es un ingreso" se atiende ANTES de revisar las
    # frases guardadas: si no, una frase corta ya enseñada (ej. "listo")
    # secuestraría la propia orden de enseñar otra.
    ensenanza = detectar_ensenanza(texto)

    if ensenanza:
        return ensenanza

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

        if accion in (
            "PAGAR_RECORDATORIO",
            "TERMINAR_ACTIVIDAD",
            "POSPONER_RECORDATORIO"
        ):

            # "Terminar actividad" ejecuta lo mismo que pagar:
            # cierra el recordatorio (si es de tipo PAGO además
            # registra el gasto; si es una ACTIVIDAD solo lo marca
            # hecho, sin mover dinero).
            if accion == "TERMINAR_ACTIVIDAD":
                accion = "PAGAR_RECORDATORIO"

            # Si no indicó qué recordatorio afecta, se toma lo que
            # sobra de lo que dijo después de quitar las palabras
            # de la frase enseñada ("ya quedó" + "Sears" -> "sears").
            if categoria:
                objetivo = categoria
            else:
                palabras_frase = set(frase_normalizada.split())
                sobrantes = [
                    p for p in texto_normalizado.split()
                    if p not in palabras_frase
                ]
                objetivo = " ".join(sobrantes) or str(fila["frase"])

            return {
                "accion": accion,
                "descripcion": objetivo
            }

    return None



def guardar_frase(usuario_id, cuenta_id, frase, accion, categoria=None):
    """
    Guarda una frase enseñada. Si ya existe la misma (ignorando
    acentos/mayúsculas) en la cuenta, la ACTUALIZA en vez de duplicarla.
    Regresa (id, actualizada). Lanza ValueError si es inválida.
    """

    frase = (frase or "").strip()
    accion = (accion or "").upper()
    categoria = (categoria or "").strip() or None

    if not frase or len(frase) > 255:
        raise ValueError("Escribe una frase (máximo 255 caracteres).")

    if accion not in ACCIONES_VALIDAS:
        raise ValueError("Acción inválida.")

    if categoria and len(categoria) > 100:
        raise ValueError("La categoría es demasiado larga.")

    clave = normalizar_texto(frase)

    existentes = obtener_dataframe(
        """
        SELECT id, frase
        FROM gastos.diccionario_usuario
        WHERE cuenta_id = :cuenta_id
        """,
        {"cuenta_id": cuenta_id},
    )

    for _, fila in existentes.iterrows():
        if normalizar_texto(str(fila["frase"])) == clave:
            ejecutar_query(
                """
                UPDATE gastos.diccionario_usuario
                SET accion = :accion, categoria = :categoria, frase = :frase
                WHERE id = :id AND cuenta_id = :cuenta_id
                """,
                {"id": int(fila["id"]), "cuenta_id": cuenta_id,
                 "accion": accion, "categoria": categoria, "frase": frase},
            )
            return int(fila["id"]), True

    ejecutar_query(
        """
        INSERT INTO gastos.diccionario_usuario
            (usuario_id, cuenta_id, frase, accion, categoria)
        VALUES (:uid, :cuenta_id, :frase, :accion, :categoria)
        """,
        {"uid": usuario_id, "cuenta_id": cuenta_id, "frase": frase,
         "accion": accion, "categoria": categoria},
    )

    return None, False


def listar_frases(cuenta_id):
    return obtener_dataframe(
        """
        SELECT id, frase, accion, categoria, fecha_creacion
        FROM gastos.diccionario_usuario
        WHERE cuenta_id = :cuenta_id
        ORDER BY id DESC
        """,
        {"cuenta_id": cuenta_id},
    )


def eliminar_frase(cuenta_id, frase_id):
    """True si borró algo (siempre acotado a la cuenta)."""

    r = ejecutar_query(
        """
        DELETE FROM gastos.diccionario_usuario
        WHERE id = :id AND cuenta_id = :cuenta_id
        """,
        {"id": frase_id, "cuenta_id": cuenta_id},
    )

    return bool(getattr(r, "rowcount", 0))
