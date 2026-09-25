import streamlit as st
import json
from datetime import datetime

from db import ejecutar_query
from db import obtener_dataframe
from services.recordatorios_service import (
    marcar_pagado,
    puede_agregar_recordatorio
)


def _resolver_fecha_movimiento(resultado):
    """
    Si el usuario mencionó cuándo pasó el gasto/ingreso ("ayer",
    "antier", "el 20 de septiembre"), la IA ya lo resolvió a
    YYYY-MM-DD y llega en resultado["fecha"]. Si no vino, se usa
    el momento actual (mismo comportamiento de siempre).

    Regresa (fecha_a_usar, aviso_o_None) — nunca bloquea el
    registro: si la fecha viene mal formada, cae a hoy y avisa.
    """

    fecha_texto = resultado.get("fecha")

    if not fecha_texto:
        return datetime.now(), None

    try:

        fecha_parseada = datetime.strptime(
            str(fecha_texto),
            "%Y-%m-%d"
        ).date()

        return (
            datetime.combine(fecha_parseada, datetime.min.time()),
            None
        )

    except ValueError:

        return (
            datetime.now(),
            " (no logré interpretar la fecha que mencionaste, "
            "se guardó con la fecha de hoy)"
        )


def ejecutar_accion(resultado):

    accion = resultado.get(
        "accion",
        ""
    ).upper()

    # =====================================
    # ABRIR INICIO
    # =====================================

    if accion == "ABRIR_INICIO":

        st.session_state["pagina_actual"] = (
            "🏠 Inicio"
        )

        st.session_state[
            "debug_accion"
        ] = "inicio"

        st.rerun()

    # =====================================
    # ABRIR DASHBOARD
    # =====================================

    if accion == "ABRIR_DASHBOARD":

        st.session_state["pagina_actual"] = (
            "Dashboard"
        )

        st.session_state[
            "debug_accion"
        ] = "dashboard"

        st.rerun()

    # =====================================
    # ABRIR RECORDATORIOS
    # =====================================

    if accion == "ABRIR_RECORDATORIOS":

        st.session_state["pagina_actual"] = (
            "Recordatorios"
        )

        st.session_state[
            "debug_accion"
        ] = "recordatorios"

        st.rerun()

    # =====================================
    # ABRIR MOVIMIENTOS
    # =====================================
    if accion == "ABRIR_MOVIMIENTOS":

        st.session_state["pagina_actual"] = (
            "Movimientos"
        )

        st.session_state[
            "debug_accion"
        ] = "movimientos"

        st.rerun()

    # =====================================
    # ABRIR HISTORIAL
    # =====================================
    if accion == "ABRIR_HISTORIAL":

        st.session_state["pagina_actual"] = (
            "Historial"
        )

        st.session_state[
            "debug_accion"
        ] = "historial"

        st.rerun()

    # =====================================
    # ABRIR PRESUPUESTO
    # =====================================
    if accion == "ABRIR_PRESUPUESTO":

        st.session_state["pagina_actual"] = (
            "Presupuesto"
        )

        st.session_state[
            "debug_accion"
        ] = "presupuesto"

        st.rerun()

    # =====================================
    # ABRIR APRENDIZAJE
    # =====================================
    if accion == "ABRIR_APRENDIZAJE":

        st.session_state["pagina_actual"] = (
            "🧠 Aprendizaje"
        )

        st.session_state[
            "debug_accion"
        ] = "aprendizaje"

        st.rerun()

    # =====================================
    # ABRIR ASISTENTE
    # =====================================
    if accion == "ABRIR_ASISTENTE":

        st.session_state["pagina_actual"] = (
            "Asistente IA"
        )

        st.session_state[
            "debug_accion"
        ] = "asistente"

        st.rerun()

    # =====================================
    # ABRIR CUENTA
    # =====================================
    if accion == "ABRIR_CUENTA":

        st.session_state["pagina_actual"] = (
            "👨‍👩‍👧 Cuenta"
        )

        st.session_state[
            "debug_accion"
        ] = "cuenta"

        st.rerun()

    # =====================================
    # ABRIR SUSCRIPCIÓN
    # =====================================
    if accion == "ABRIR_SUSCRIPCION":

        st.session_state["pagina_actual"] = (
            "💳 Suscripción"
        )

        st.session_state[
            "debug_accion"
        ] = "suscripcion"

        st.rerun()
        
    # =====================================
    # PREGUNTAR MONTO INGRESO
    # =====================================

    if accion == "PREGUNTAR_MONTO_INGRESO":

        st.session_state[
            "esperando_monto_ingreso"
        ] = True

        return (
            "💰 Detecté un ingreso.\n\n"
            "¿Cuál fue el monto?"
        )

    # =====================================
    # POSPONER RECORDATORIO
    # =====================================

    if accion == "POSPONER_RECORDATORIO":

        descripcion = resultado.get(
            "descripcion",
            ""
        )

        recordatorios = obtener_dataframe(
            """
            SELECT *
            FROM gastos.recordatorios
            WHERE cuenta_id = :cuenta_id
            AND pagado = FALSE
            """,
            {"cuenta_id": st.session_state["cuenta_id"]}
        )

        if recordatorios.empty:

            return (
                "⚠ No existen recordatorios pendientes."
            )

        coincidencia = recordatorios[
            recordatorios["descripcion"]
            .str.upper()
            .str.contains(
                descripcion.upper(),
                na=False
            )
        ]

        if coincidencia.empty:

            return (
                f"⚠ No encontré {descripcion}"
            )

        row = coincidencia.iloc[0]

        ejecutar_query(
            """
            UPDATE gastos.recordatorios
            SET
                fecha_proxima_alerta =
                CURRENT_DATE + INTERVAL '1 day'
            WHERE id = :id
            """,
            {
                "id": int(row["id"])
            }
        )

        return (
            f"⏰ Te recordaré mañana: "
            f"{row['descripcion']}"
        )

    # =====================================
    # PAGAR RECORDATORIO
    # =====================================

    if accion == "PAGAR_RECORDATORIO":

        descripcion = resultado.get(
            "descripcion",
            ""
        )

        recordatorios = obtener_dataframe(
            """
            SELECT *
            FROM gastos.recordatorios
            WHERE cuenta_id = :cuenta_id
            AND pagado = FALSE
            """,
            {"cuenta_id": st.session_state["cuenta_id"]}
        )

        if recordatorios.empty:

            return (
                "⚠ No existen recordatorios pendientes."
            )

        coincidencia = recordatorios[
            recordatorios["descripcion"]
            .str.upper()
            .str.contains(
                descripcion.upper(),
                na=False
            )
        ]

        if coincidencia.empty:

            return (
                f"⚠ No encontré {descripcion}"
            )

        row = coincidencia.iloc[0]

        marcar_pagado(
            int(row["id"]),
            row["fecha_vencimiento"],
            row["frecuencia"]
        )

        es_pago = row.get("tipo", "PAGO") == "PAGO"

        if es_pago:

            ejecutar_query(
                """
                INSERT INTO gastos.movimientos
                (
                    usuario_id,
                    cuenta_id,
                    tipo,
                    categoria,
                    concepto,
                    monto,
                    texto_original
                )
                VALUES
                (
                    :uid,
                    :cuenta_id,
                    'GASTO',
                    'Recordatorio',
                    :concepto,
                    :monto,
                    :texto
                )
                """,
                {
                    "uid":
                        st.session_state["user_id"],

                    "cuenta_id":
                        st.session_state["cuenta_id"],

                    "concepto":
                        row["descripcion"],

                    "monto":
                        float(row["monto"] or 0),

                    "texto":
                        f"Pago automático de {row['descripcion']}"
                }
            )

        if str(row["frecuencia"]).upper() == "UNICO":

            return (
                f"✅ Marqué como {'pagado' if es_pago else 'hecho'} "
                f"{row['descripcion']}"
            )

        return (
            f"✅ Registré el pago de "
            f"{row['descripcion']}.\n\n"
            f"Seguirá activo por ser "
            f"{row['frecuencia']}."
        )

    # =====================================
    # REGISTRAR GASTO
    # =====================================

    if accion == "REGISTRAR_GASTO":

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        if monto <= 0:

            return (
                "⚠ No pude identificar "
                "el importe del gasto."
            )

        fecha_movimiento, aviso_fecha = _resolver_fecha_movimiento(
            resultado
        )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                cuenta_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original,
                fecha
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                'GASTO',
                :categoria,
                :concepto,
                :monto,
                :texto,
                :fecha
            )
            """,
            {
                "uid":
                    st.session_state["user_id"],

                "cuenta_id":
                    st.session_state["cuenta_id"],

                "categoria":
                    resultado.get(
                        "categoria",
                        "Otros"
                    ),

                "concepto":
                    resultado.get(
                        "concepto",
                        "Gasto"
                    ),

                "monto":
                    monto,

                "texto":
                    resultado.get(
                        "texto_original",
                        ""
                    ),

                "fecha":
                    fecha_movimiento
            }
        )

        return (
            f"✅ Gasto registrado "
            f"${monto:,.2f}"
            f"{f' el {fecha_movimiento:%d/%m/%Y}' if resultado.get('fecha') else ''}"
            f"{aviso_fecha or ''}"
        )

    # =====================================
    # REGISTRAR INGRESO
    # =====================================

    if accion == "REGISTRAR_INGRESO":

        monto = float(
            resultado.get(
                "monto",
                0
            )
        )

        if monto <= 0:

            return (
                "⚠ No pude identificar "
                "el importe del ingreso."
            )

        fecha_movimiento, aviso_fecha = _resolver_fecha_movimiento(
            resultado
        )

        ejecutar_query(
            """
            INSERT INTO gastos.movimientos
            (
                usuario_id,
                cuenta_id,
                tipo,
                categoria,
                concepto,
                monto,
                texto_original,
                origen_ingreso,
                fecha
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                'INGRESO',
                'Ingreso',
                :concepto,
                :monto,
                :texto,
                :origen,
                :fecha
            )
            """,
            {
                "uid":
                    st.session_state["user_id"],

                "cuenta_id":
                    st.session_state["cuenta_id"],

                "concepto":
                    resultado.get(
                        "concepto",
                        "Ingreso"
                    ),

                "monto":
                    monto,

                "texto":
                    resultado.get(
                        "texto_original",
                        ""
                    ),

                "origen":
                    resultado.get(
                        "origen_ingreso",
                        "Otro"
                    ),

                "fecha":
                    fecha_movimiento
            }
        )

        return (
            f"✅ Ingreso registrado "
            f"${monto:,.2f}"
            f"{f' el {fecha_movimiento:%d/%m/%Y}' if resultado.get('fecha') else ''}"
            f"{aviso_fecha or ''}"
        )

    # =====================================
    # CREAR RECORDATORIO (por voz o texto)
    # =====================================

    if accion == "CREAR_RECORDATORIO":

        cuenta_id = st.session_state["cuenta_id"]

        descripcion = str(
            resultado.get("descripcion", "")
        ).strip()

        tipo_recordatorio = str(
            resultado.get("tipo", "PAGO")
        ).upper()

        if tipo_recordatorio not in ("PAGO", "ACTIVIDAD"):
            tipo_recordatorio = "PAGO"

        es_pago = tipo_recordatorio == "PAGO"

        monto = (
            float(resultado.get("monto", 0) or 0)
            if es_pago else None
        )

        fecha_vencimiento = resultado.get(
            "fecha_vencimiento"
        )

        frecuencia = str(
            resultado.get("frecuencia", "UNICO")
        ).upper()

        if frecuencia not in (
            "UNICO", "SEMANAL", "QUINCENAL", "MENSUAL", "ANUAL"
        ):
            frecuencia = "UNICO"

        dias_anticipacion = int(
            resultado.get("dias_anticipacion", 3) or 3
        )

        if not descripcion or not fecha_vencimiento:

            return (
                "⚠ No pude identificar bien la descripción o la "
                "fecha del recordatorio. Intenta de nuevo siendo "
                "más específico, por ejemplo: 'recuérdame pagar "
                "la tarjeta Sears el 30 de este mes por 1300 "
                "pesos' o 'recuérdame tramitar mi tarjeta de "
                "residente en septiembre de 2027'."
            )

        try:

            fecha_vencimiento = datetime.strptime(
                str(fecha_vencimiento),
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return (
                "⚠ No logré entender bien la fecha. Intenta "
                "decirla de forma más clara, por ejemplo "
                "'el 30 de este mes' o 'el próximo viernes'."
            )

        puede, mensaje_limite = puede_agregar_recordatorio(
            cuenta_id
        )

        if not puede:
            return f"⚠ {mensaje_limite}"

        ejecutar_query(
            """
            INSERT INTO gastos.recordatorios
            (
                usuario_id,
                cuenta_id,
                descripcion,
                monto,
                fecha_vencimiento,
                dias_anticipacion,
                frecuencia,
                tipo
            )
            VALUES
            (
                :uid,
                :cuenta_id,
                :descripcion,
                :monto,
                :fecha_vencimiento,
                :dias,
                :frecuencia,
                :tipo
            )
            """,
            {
                "uid": st.session_state["user_id"],
                "cuenta_id": cuenta_id,
                "descripcion": descripcion,
                "monto": monto,
                "fecha_vencimiento": fecha_vencimiento,
                "dias": dias_anticipacion,
                "frecuencia": frecuencia,
                "tipo": tipo_recordatorio
            }
        )

        if es_pago:

            return (
                f"🔔 Recordatorio creado: {descripcion} "
                f"(${monto:,.2f}), vence {fecha_vencimiento}."
            )

        return (
            f"📌 Pendiente anotado: {descripcion}, "
            f"vence {fecha_vencimiento}."
        )

    # =====================================
    # REPETIR RESUMEN DEL DÍA
    # =====================================

    if accion == "REPETIR_RESUMEN":

        from services.narrativa_service import generar_narrativa_ia
        from services.billing_service import obtener_plan_actual

        cuenta_id = st.session_state["cuenta_id"]

        plan = obtener_plan_actual(cuenta_id)

        usar_ia = bool(
            plan is not None
            and plan.get("incluye_ia", True)
        )

        return generar_narrativa_ia(cuenta_id, usar_ia=usar_ia)

    # =====================================
    # CONSULTA GENERAL (consejo, preguntas
    # abiertas, cálculos, "¿me conviene...")
    # =====================================

    if accion == "CONSULTA_GENERAL":

        from services.narrativa_service import (
            calcular_datos_proyeccion
        )
        from services.currency_service import (
            obtener_tipo_cambio_usd_mxn
        )
        from services.ai_client import (
            get_openai_client,
            get_deployment
        )

        cuenta_id = st.session_state["cuenta_id"]

        pregunta = (
            resultado.get("pregunta")
            or resultado.get("texto_original")
            or ""
        )

        contexto = calcular_datos_proyeccion(cuenta_id)

        pregunta_lower = pregunta.lower()

        menciona_dolar = any(
            palabra in pregunta_lower
            for palabra in (
                "dolar", "dólar", "usd", "tipo de cambio",
                "divisa", "moneda extranjera"
            )
        )

        if menciona_dolar:

            tipo_cambio = obtener_tipo_cambio_usd_mxn()

            if tipo_cambio is not None:

                contexto["tipo_cambio_usd_mxn_hoy"] = round(
                    tipo_cambio["valor"], 2
                )

                contexto["tipo_cambio_actualizado"] = (
                    tipo_cambio["fecha_actualizacion"]
                )

        prompt_sistema = (
            "Eres el asistente financiero de Queda, hablando en "
            "voz/texto con el usuario de forma conversacional. "
            "Te doy un JSON de contexto con su situación "
            "financiera actual (y el tipo de cambio USD/MXN de "
            "hoy, SOLO si viene incluido) y su pregunta.\n\n"
            "Reglas:\n"
            "- Usa ÚNICAMENTE las cifras del contexto — nunca "
            "inventes montos, tipo de cambio, ni datos que no "
            "estén ahí.\n"
            "- Si preguntan por el dólar y 'tipo_cambio_usd_mxn_hoy' "
            "NO viene en el contexto, dilo honestamente en vez de "
            "inventar un número.\n"
            "- Si piden un cálculo (ahorro semanal, proyección, "
            "etc.), hazlo tú mismo con las cifras que tengas y "
            "muestra el resultado.\n"
            "- Tono cálido, natural, en español de México, en "
            "prosa corrida — nada de listas ni tablas.\n"
            "- PROHIBIDO usar backticks, asteriscos o cualquier "
            "símbolo de markdown.\n"
            "- Máximo 5 líneas."
        )

        try:

            client = get_openai_client()
            deployment = get_deployment()

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {
                        "role": "system",
                        "content": prompt_sistema
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Contexto: "
                            f"{json.dumps(contexto, ensure_ascii=False, default=str)}"
                            f"\n\nPregunta: {pregunta}"
                        )
                    }
                ],
                temperature=0.4,
                max_tokens=280
            )

            respuesta_texto = (
                response.choices[0].message.content.strip()
            )

            respuesta_texto = (
                respuesta_texto
                .replace("`", "")
                .replace("**", "")
                .replace("*", "")
            )

            return respuesta_texto

        except Exception as e:

            return (
                f"⚠ No pude generar una respuesta ahora mismo: {e}"
            )

    return "⚠ Acción no reconocida"