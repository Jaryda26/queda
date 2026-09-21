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

    reemplazos = {

        "nom ina": "nomina",

        "bbva bancomer": "bbva",

        "gasolina premium": "gasolina",
        "gasolina magna": "gasolina",

        "uber eats": "comida",
        "didi food": "comida",

        "pago de nomina": "nomina",
        "pago nomina": "nomina",

        "ya cago el aguila": "ya cayo el aguila",
        "ya cago la quincena": "ya cayo la quincena"
    }

    for viejo, nuevo in reemplazos.items():

        texto = texto.replace(
            viejo,
            nuevo
        )

    return texto


def detectar_categoria(texto):

    texto = normalizar_texto(texto)

    categorias = {

        "Gasolina": [
            "gasolina",
            "pemex",
            "shell",
            "mobil",
            "combustible",
            "diesel"
        ],

        "Comida": [
            "comida",
            "tacos",
            "pizza",
            "hamburguesa",
            "restaurante",
            "coca",
            "refresco",
            "cafe",
            "cafeteria"
        ],

        "Servicios": [
            "internet",
            "luz",
            "agua",
            "telefono",
            "celular",
            "telmex",
            "izzi",
            "totalplay"
        ],

        "Transporte": [
            "uber",
            "didi",
            "taxi",
            "caseta",
            "casetas",
            "estacionamiento"
        ],

        "Salud": [
            "doctor",
            "medico",
            "hospital",
            "farmacia",
            "medicina"
        ],

        "Entretenimiento": [
            "netflix",
            "spotify",
            "cine",
            "disney",
            "amazon prime"
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

    # ====================================
    # PAGAR RECORDATORIOS
    # ====================================

    pagos = [

        "ya pague",
        "ya pagué",

        "quedo pagado",
        "quedó pagado",

        "liquide",
        "liquidé",

        "liquidado"
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
                "accion":
                    "PAGAR_RECORDATORIO",

                "descripcion":
                    descripcion.strip(),

                "texto_original":
                    texto_original
            }

    # ====================================
    # POSPONER RECORDATORIOS
    # ====================================

    posponer = [

        "despues",
        "después",

        "luego",

        "mas tarde",
        "más tarde",

        "recordarme manana",
        "recordame manana",

        "manana",
        "mañana"
    ]

    for palabra in posponer:

        if palabra in texto:

            descripcion = texto.replace(
                palabra,
                ""
            )

            return {
                "accion":
                    "POSPONER_RECORDATORIO",

                "descripcion":
                    descripcion.strip(),

                "texto_original":
                    texto_original
            }

    # ====================================
    # DASHBOARD
    # ====================================

    dashboard = [

        "dashboard",

        "estadisticas",
        "estadísticas",

        "como voy",
        "cómo voy",

        "mi resumen",
        "resumen",

        "mis gastos",

        "cuanto me queda",
        "cuánto me queda"
    ]

    for palabra in dashboard:

        if palabra in texto:

            return {
                "accion":
                    "ABRIR_DASHBOARD"
            }

    # ====================================
    # RECORDATORIOS
    # ====================================

    recordatorios = [

        "que tengo pendiente",
        "qué tengo pendiente",

        "recordatorios",

        "pendientes",

        "vencimientos",

        "que debo pagar",
        "qué debo pagar"
    ]

    for palabra in recordatorios:

        if palabra in texto:

            return {
                "accion":
                    "ABRIR_RECORDATORIOS"
            }

    # ====================================
    # INGRESOS SIN MONTO
    # ====================================

    ingresos_sin_monto = [

        # águila

        "ya cayo el aguila",
        "ya cayó el águila",

        "ya cago el aguila",
        "ya cagó el águila",

        # marrana

        "ya chillo la marrana",
        "ya chillo la marrana",
        "ya chilló la marrana",

        # feria

        "me cayo una feria",
        "me cayó una feria",

        "me cayo lana",
        "me cayó lana",

        "ya me cayo",
        "ya me cayó",

        "cayo dinero",
        "cayó dinero",

        # pagos

        "me pagaron",

        "me depositaron",

        "me transfirieron",

        # nomina

        "nomina",
        "nómina",

        "salario",

        "pago de nomina",
        "pago de nómina",

        # extras

        "aguinaldo",
        "utilidades",

        "bono",

        "comision",
        "comisión",
        "comisiones",

        "prestamo",
        "préstamo",

        "reembolso",

        "devolucion",
        "devolución",

        "vendi",
        "vendí",

        "venta"
    ]

    for palabra in ingresos_sin_monto:

        if palabra in texto:

            return {
                "accion":
                    "PREGUNTAR_MONTO_INGRESO",

                "texto_original":
                    texto_original
            }

    # ====================================
    # GASTOS
    # ====================================

    gastos = [

        "compre",
        "compré",

        "gaste",
        "gasté",

        "consumi",
        "consumí",

        "inverti",
        "invertí",

        "gasolina",

        "uber",
        "taxi",

        "tacos",
        "comida",

        "coca",
        "refresco",

        "internet",
        "luz",
        "agua",

        "netflix",
        "spotify",
        "prime",

        "sanborns",
        "sears",

        "farmacia",
        "doctor",

        "se me fue",

        "me compre",
        "me compré"
    ]

    for palabra in gastos:

        if palabra in texto:

            return {
                "accion":
                    "REGISTRAR_GASTO",

                "categoria":
                    detectar_categoria(texto),

                "texto_original":
                    texto_original
            }

    return None