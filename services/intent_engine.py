import unicodedata


def normalizar_texto(texto):

    texto = texto.lower().strip()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c) != "Mn"
    )

    return texto


def detectar_categoria(texto):

    categorias = {

        "Gasolina": [
            "gasolina",
            "pemex",
            "shell",
            "mobil",
            "combustible"
        ],

        "Comida": [
            "comida",
            "tacos",
            "restaurante",
            "pizza",
            "coca",
            "refresco",
            "cafe"
        ],

        "Servicios": [
            "internet",
            "luz",
            "agua",
            "telefono",
            "telmex"
        ],

        "Transporte": [
            "uber",
            "didi",
            "taxi",
            "casetas"
        ],

        "Salud": [
            "doctor",
            "medico",
            "hospital",
            "farmacia"
        ],

        "Entretenimiento": [
            "netflix",
            "spotify",
            "cine"
        ]
    }

    for categoria, palabras in categorias.items():

        for palabra in palabras:

            if palabra in texto:

                return categoria

    return "Otros"


def detectar_intencion(texto):

    texto_original = texto

    texto = normalizar_texto(texto)

    ingresos = [
        "ya cayo el aguila",
        "ya me cayo",
        "me pagaron",
        "me depositaron",
        "nomina",
        "salario",
        "comision",
        "comisiones",
        "aguinaldo",
        "utilidades",
        "bono",
        "vendi",
        "venta",
        "prestamo",
        "reembolso",
        "pago de nomina",
        "pago de salario"
    ]

    for palabra in ingresos:

        if palabra in texto:

            return {
                "accion": "PREGUNTAR_MONTO_INGRESO",
                "texto_original": texto_original
            }

    pagos = [
        "ya pague",
        "ya pague sears",
        "ya pague bbva",
        "liquide",
        "quedo pagado"
    ]

    for palabra in pagos:

        if palabra in texto:

            descripcion = texto

            for p in pagos:
                descripcion = descripcion.replace(
                    p,
                    ""
                )

            return {
                "accion": "PAGAR_RECORDATORIO",
                "descripcion": descripcion.strip(),
                "texto_original": texto_original
            }

    posponer = [
        "despues",
        "después",
        "mas tarde",
        "más tarde",
        "luego",
        "mañana"
    ]

    for palabra in posponer:

        if palabra in texto:

            descripcion = texto.replace(
                palabra,
                ""
            )

            return {
                "accion": "POSPONER_RECORDATORIO",
                "descripcion": descripcion.strip(),
                "texto_original": texto_original
            }

    gastos = [
        "compre",
        "compré",
        "gaste",
        "gasté",
        "pague",
        "pagué",
        "gasolina",
        "uber",
        "coca",
        "tacos",
        "internet",
        "comida"
    ]

    for palabra in gastos:

        if palabra in texto:

            return {
                "accion": "REGISTRAR_GASTO",
                "categoria": detectar_categoria(texto),
                "texto_original": texto_original
            }

    return None