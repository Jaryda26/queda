import re
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

    # Azure Speech transcribe con puntuación natural ("Ya, cagó
    # el águila." / "¿Ya cagó el águila?"), y esa puntuación
    # rompía las comparaciones de texto exacto de abajo (una
    # coma de más y "ya cago el aguila" deja de aparecer como
    # substring). La quitamos aquí, antes de comparar cualquier
    # cosa — así da igual cómo puntúe Azure la frase.

    texto = re.sub(
        r"[,.!?¡¿;:()\"']",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    reemplazos = {

        "nom ina": "nomina",

        "bbva bancomer": "bbva",

        "gasolina premium": "gasolina",
        "gasolina magna": "gasolina",

        "uber eats": "comida",
        "didi food": "comida",

        "pago de nomina": "nomina",
        "pago nomina": "nomina",

        "ya cago el aguila": "ya cayo el aguila"
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
            "cafe"
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
            "casetas",
            "caseta",
            "estacionamiento"
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
            "cine",
            "amazon prime",
            "disney"
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

    # ======================================
    # INICIO
    # ======================================

    inicio = [
        "inicio",
        "home",
        "pantalla inicial",
        "pantalla principal"
    ]

    for palabra in inicio:

        if palabra in texto:

            return {
                "accion": "ABRIR_INICIO"
            }

    # ======================================
    # DASHBOARD
    # ======================================

    dashboard = [
        "dashboard",
        "estadisticas",
        "estadísticas",
        "como voy",
        "cómo voy",
        "mis gastos",
        "mi resumen",
        "resumen",
        "cuanto me queda",
        "cuánto me queda"
    ]

    for palabra in dashboard:

        if palabra in texto:

            return {
                "accion": "ABRIR_DASHBOARD"
            }

        # ======================================
    # MOVIMIENTOS
    # ======================================

    movimientos = [

        "movimientos",
        "capturas",
        "captura",
        "registro de gastos"
    ]

    for palabra in movimientos:

        if palabra in texto:

            return {
                "accion": "ABRIR_MOVIMIENTOS"
            }

    # ======================================
    # HISTORIAL
    # ======================================

    historial = [

        "historial",
        "mis movimientos",
        "todas mis compras",
        "todos mis gastos"
    ]

    for palabra in historial:

        if palabra in texto:

            return {
                "accion": "ABRIR_HISTORIAL"
            }

    # ======================================
    # PRESUPUESTO
    # ======================================

    presupuesto = [

        "presupuesto",
        "mi presupuesto",
        "configurar presupuesto"
    ]

    for palabra in presupuesto:

        if palabra in texto:

            return {
                "accion": "ABRIR_PRESUPUESTO"
            }

    # ======================================
    # APRENDIZAJE
    # ======================================

    aprendizaje = [

        "aprendizaje",
        "frases aprendidas",
        "diccionario",
        "diccionario personal"
    ]

    for palabra in aprendizaje:

        if palabra in texto:

            return {
                "accion": "ABRIR_APRENDIZAJE"
            }

    # ======================================
    # ASISTENTE
    # ======================================

    asistente = [

        "asistente",
        "ia",
        "inteligencia artificial"
    ]

    for palabra in asistente:

        if palabra in texto:

            return {
                "accion": "ABRIR_ASISTENTE"
            }

    # ======================================
    # CUENTA (miembros / invitación)
    # ======================================

    cuenta = [

        "mi cuenta",
        "abre cuenta",
        "abre mi cuenta",
        "miembros",
        "familia",
        "codigo de invitacion",
        "código de invitación"
    ]

    for palabra in cuenta:

        if palabra in texto:

            return {
                "accion": "ABRIR_CUENTA"
            }

    # ======================================
    # SUSCRIPCIÓN / PLAN
    # ======================================

    suscripcion = [

        "suscripcion",
        "suscripción",
        "mi plan",
        "planes",
        "membresia",
        "membresía",
        "cambiar de plan",
        "metodo de pago",
        "método de pago"
    ]

    for palabra in suscripcion:

        if palabra in texto:

            return {
                "accion": "ABRIR_SUSCRIPCION"
            }

    # ======================================
    # REPETIR RESUMEN DEL DÍA
    # ======================================

    resumen = [
        "repite el resumen",
        "repiteme el resumen",
        "repíteme el resumen",
        "dame el resumen",
        "dame el contexto",
        "cual es mi resumen",
        "cuál es mi resumen",
        "recuerdame mi situacion",
        "recuérdame mi situación",
        "como voy",
        "cómo voy"
    ]

    for palabra in resumen:

        if palabra in texto:

            return {
                "accion": "REPETIR_RESUMEN"
            }



    # ======================================
    # RECORDATORIOS
    # ======================================

    recordatorios = [
        "recordatorios",
        "pendientes",
        "vencimientos",
        "que tengo pendiente",
        "qué tengo pendiente",
        "que debo pagar",
        "qué debo pagar"
    ]

    for palabra in recordatorios:

        if palabra in texto:

            return {
                "accion": "ABRIR_RECORDATORIOS"
            }

    # ======================================
    # PAGAR RECORDATORIO
    # ======================================

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
                "accion": "PAGAR_RECORDATORIO",
                "descripcion": descripcion.strip(),
                "texto_original": texto_original
            }

    # ======================================
    # POSPONER RECORDATORIO
    # ======================================

    posponer = [
        "despues",
        "después",
        "luego",
        "mas tarde",
        "más tarde",
        "mañana",
        "manana",
        "recordarme manana",
        "recordame manana"
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

    # ======================================
    # INGRESOS SIN MONTO
    # ======================================

    ingresos_sin_monto = [

        "ya cayo el aguila",
        "ya cayó el águila",
        "cayo el aguila",
        "cayó el águila",

        "ya cago el aguila",
        "ya cagó el águila",
        "cago el aguila",
        "cagó el águila",

        "ya chillo la marrana",
        "ya chilló la marrana",
        "chillo la marrana",
        "chilló la marrana",

        "ya cayo la quincena",
        "ya cayó la quincena",

        "ya cayo la raya",
        "ya cayó la raya",

        "me cayo una feria",
        "me cayó una feria",

        "me cayo lana",
        "me cayó lana",

        "ya me cayo",
        "ya me cayó",

        "cayo dinero",
        "cayó dinero",

        "ya entro dinero",
        "ya entró dinero",

        "me pagaron",
        "ya me pagaron",

        "me depositaron",
        "ya me depositaron",

        "me transfirieron",

        "nomina",
        "nómina",

        "salario",

        "pago de nomina",
        "pago de nómina",

        "pago de salario",

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
                "accion": "PREGUNTAR_MONTO_INGRESO",
                "texto_original": texto_original
            }

    # ======================================
    # GASTOS
    # ======================================
    #
    # NO SE INTERCEPTAN.
    #
    # Se dejan pasar a OpenAI
    # para extraer:
    #
    # concepto
    # categoria
    # monto
    #
    # Ejemplo:
    #
    # Compré una coca de 25 pesos
    #
    # ↓
    #
    # OpenAI:
    #
    # {
    #   "accion":"REGISTRAR_GASTO",
    #   "concepto":"Coca",
    #   "categoria":"Comida",
    #   "monto":25
    # }
    #
    # ======================================

    return None