from services.estado_voz import st
import json
import logging
import re
from datetime import datetime

from db import ejecutar_query
from db import obtener_dataframe
from services.intent_engine import (
    extraer_monto_flexible,
    normalizar_texto,
)
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


def _buscar_recordatorios(recordatorios, descripcion):
    """
    Busca recordatorios cuya descripción corresponda a lo que dijo
    el usuario, ignorando acentos y mayúsculas en AMBOS lados.

    Antes se comparaba el texto ya sin acentos ("tramite") contra
    la descripción guardada CON acentos ("Trámite"), así que
    cualquier recordatorio con acento nunca se encontraba. Además
    str.contains() trataba el texto como expresión regular.

    Coincide si el texto dicho aparece completo dentro de la
    descripción, o si todas sus palabras aparecen (en cualquier
    orden) — así "comprar pastel" encuentra "Comprar un pastel".
    """

    buscado = normalizar_texto(descripcion)

    if not buscado:
        return recordatorios.iloc[0:0]

    palabras = buscado.split()

    def coincide(descripcion_guardada):

        guardada = normalizar_texto(str(descripcion_guardada))

        if buscado in guardada:
            return True

        palabras_guardada = guardada.split()

        return all(p in palabras_guardada for p in palabras)

    mascara = recordatorios["descripcion"].apply(coincide)

    return recordatorios[mascara]


log = logging.getLogger("queda.acciones")


def _consejo_personal(cuenta_id, pregunta):
    """
    Consejos basados en los números del usuario. Siempre se calculan; si
    el plan incluye IA (y queda cupo del día) la IA los redacta de forma
    más personal usando SOLO esas cifras.
    """

    from services import insights_service as ins
    from services.billing_service import obtener_plan_actual
    from services.plan_ia_service import (
        consumir_ia,
        devolver_ia,
    )

    try:
        base = ins.consejo_texto(cuenta_id)
    except Exception:
        log.exception("Falló el cálculo de consejos")
        return "⚠ No pude calcular tus consejos ahora mismo."

    plan = obtener_plan_actual(cuenta_id)

    if plan is None or not plan.get("incluye_ia", False):
        return (
            base + " Con el plan Individual o Familiar te doy consejos "
            "personalizados con inteligencia artificial."
        )

    permitido, _, limite = consumir_ia(cuenta_id, plan)

    if not permitido:
        return (
            base + f" (Llegaste a tu límite de {limite} consultas con IA "
            "de hoy; estos consejos son calculados. El cupo se "
            "reinicia a medianoche.)"
        )

    try:

        from services.ai_client import get_openai_client, get_deployment

        contexto = ins.contexto_financiero(cuenta_id)

        prompt_sistema = (
            "Eres el asesor financiero personal de Queda y hablas con el "
            "usuario por voz/texto. Te doy un JSON con SUS números reales "
            "(periodo, presupuesto, categorías, metas) y su pregunta.\n\n"
            "Reglas:\n"
            "- Usa ÚNICAMENTE cifras del contexto; nunca inventes montos.\n"
            "- Sé específico y personal: nombra sus categorías y montos, "
            "y da 2 o 3 acciones concretas que pueda hacer esta semana.\n"
            "- Si tiene metas de ahorro, conéctalas con el consejo.\n"
            "- Si faltan datos, dilo y sugiere registrar más gastos.\n"
            "- Tono cálido y directo, español de México, prosa corrida: "
            "sin listas, sin tablas, sin markdown ni asteriscos.\n"
            "- Máximo 6 líneas."
        )

        response = get_openai_client().chat.completions.create(
            model=get_deployment(),
            messages=[
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user",
                    "content": (
                        "Contexto: "
                        + json.dumps(contexto, ensure_ascii=False, default=str)
                        + "\n\nPregunta: "
                        + (pregunta or "Dame un consejo para mejorar mis finanzas")
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=380,
        )

        texto = (response.choices[0].message.content or "").strip()
        texto = texto.replace("`", "").replace("**", "").replace("*", "")

        if not texto:
            raise RuntimeError("respuesta vacía")

        return texto

    except Exception:

        devolver_ia(cuenta_id)
        log.exception("Falló el consejo con IA; se usan los calculados")

        return base


def _lista_metas(metas):
    return ", ".join(m["nombre"] for m in metas)


def _accion_meta(accion, resultado):
    """CREAR_META / ABONAR_META / CONSULTAR_METAS. Lanza ValueError con
    un mensaje listo para el usuario."""

    from services import metas_service as ms

    cuenta_id = st.session_state["cuenta_id"]
    user_id = st.session_state["user_id"]

    if accion == "CREAR_META":

        if resultado.get("error") == "sin_monto":
            raise ValueError(
                "No alcancé a oír cuánto quieres ahorrar. Dilo así: "
                "quiero ahorrar 10 mil pesos para vacaciones."
            )

        plazo = resultado.get("plazo")

        limite = (
            ms.fecha_desde_plazo(plazo["cantidad"], plazo["unidad"])
            if plazo else None
        )

        meta = ms.crear_meta(
            user_id, cuenta_id, resultado["nombre"],
            resultado["monto"], limite,
        )

        texto = (
            f"🎯 Meta creada: {meta['nombre']} por "
            f"${meta['monto_objetivo']:,.2f}."
        )

        if meta["ahorro_semanal_sugerido"]:
            texto += (
                f" Para llegar en {meta['dias_restantes']} días necesitas "
                f"apartar ${meta['ahorro_semanal_sugerido']:,.2f} por semana."
            )

        return texto + f" Para abonar di: abona 500 a {meta['nombre']}."

    if accion == "ABONAR_META":

        if resultado.get("error") == "sin_monto":
            raise ValueError(
                "No alcancé a oír el monto. Dilo así: abona 500 pesos "
                "a mi meta de vacaciones."
            )

        nombre = resultado.get("meta") or ""
        activas = [m for m in ms.listar_metas(cuenta_id) if not m["completada"]]

        if not activas:
            raise ValueError(
                "No tienes metas activas. Crea una diciendo: quiero "
                "ahorrar 10 mil pesos para vacaciones."
            )

        if nombre:
            meta, candidatas = ms.buscar_meta(cuenta_id, nombre, solo_activas=True)
            if meta is None and candidatas:
                raise ValueError(
                    f"¿A cuál meta? Tienes: {_lista_metas(candidatas)}."
                )
            if meta is None:
                raise ValueError(
                    f"No encontré una meta que se llame {nombre}. "
                    f"Tus metas: {_lista_metas(activas)}."
                )
        elif len(activas) == 1:
            meta = activas[0]
        else:
            raise ValueError(
                f"¿A cuál meta? Tienes: {_lista_metas(activas)}. "
                "Dilo así: abona 500 a vacaciones."
            )

        monto = float(resultado["monto"])
        meta = ms.abonar(user_id, cuenta_id, meta["id"], monto)

        texto = (
            f"✅ {'Abonaste' if monto > 0 else 'Retiraste'} "
            f"${abs(monto):,.2f} "
            f"{'a' if monto > 0 else 'de'} {meta['nombre']}. "
            f"Llevas ${meta['ahorrado']:,.2f} de "
            f"${meta['monto_objetivo']:,.2f} ({meta['porcentaje']:.0f}%)."
        )

        if meta["completada"]:
            texto += " 🎉 ¡Meta cumplida, felicidades!"
        else:
            texto += f" Te faltan ${meta['faltante']:,.2f}."

        return texto

    # CONSULTAR_METAS
    nombre = resultado.get("meta") or ""

    if nombre:
        meta, candidatas = ms.buscar_meta(cuenta_id, nombre)
        if meta:
            return ms.describir_meta(meta)
        if candidatas:
            return " ".join(ms.describir_meta(m) for m in candidatas[:3])

    return ms.resumen_metas(cuenta_id)


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
    # CAMBIAR PRESUPUESTO ("pon mi presupuesto semanal en 2000")
    # =====================================
    if accion == "CAMBIAR_PRESUPUESTO":

        from services.presupuesto_service import (
            guardar_presupuesto,
            obtener_estado_presupuesto,
        )

        monto = resultado.get("monto")

        if monto is None:
            return (
                "No alcancé a oír el monto. Dilo así: "
                "pon mi presupuesto semanal en 2000 pesos."
            )

        actual = obtener_estado_presupuesto(
            st.session_state["cuenta_id"]
        )

        tipo = (
            resultado.get("tipo_periodo")
            or (actual["tipo_periodo"] if actual else "MENSUAL")
        )

        try:
            nuevo = guardar_presupuesto(
                st.session_state["user_id"],
                st.session_state["cuenta_id"],
                tipo,
                monto,
            )
        except ValueError as e:
            return f"No pude cambiar el presupuesto: {e}"

        etiqueta = {
            "SEMANAL": "semanal",
            "QUINCENAL": "quincenal",
            "MENSUAL": "mensual",
        }[nuevo["tipo_periodo"]]

        return (
            f"✅ Presupuesto {etiqueta} en ${nuevo['monto']:,.2f}. "
            f"Llevas ${nuevo['gastado']:,.2f} gastados "
            f"({nuevo['porcentaje']:.0f}%)."
        )

    # =====================================
    # APRENDER FRASE ("aprende que X es un ingreso")
    # =====================================
    if accion == "APRENDER_FRASE":

        from services.aprendizaje_service import guardar_frase

        error = resultado.get("error")

        if error == "sin_accion":
            return (
                "Dime qué significa. Por ejemplo: aprende que "
                "ya chilló la marrana es un ingreso."
            )

        if error == "frase_invalida":
            return (
                "Esa frase es muy corta o muy genérica para "
                "aprenderla. Usa una frase más específica."
            )

        etiquetas = {
            "REGISTRAR_INGRESO": "un ingreso",
            "REGISTRAR_GASTO": "un gasto",
            "PAGAR_RECORDATORIO": "un pago realizado",
            "TERMINAR_ACTIVIDAD": "una actividad terminada",
            "POSPONER_RECORDATORIO": "posponer un recordatorio",
        }

        try:
            _, actualizada = guardar_frase(
                st.session_state["user_id"],
                st.session_state["cuenta_id"],
                resultado["frase"],
                resultado["accion_aprendida"],
                resultado.get("categoria"),
            )
        except ValueError as e:
            return f"No pude guardar esa frase: {e}"

        verbo = "Actualicé" if actualizada else "Aprendí"

        return (
            f"🧠 {verbo}: \"{resultado['frase']}\" ahora es "
            f"{etiquetas[resultado['accion_aprendida']]}. "
            "Puedes borrarla en Aprendizaje."
        )

    # =====================================
    # CONSULTAS CALCULADAS (sin IA, todos los planes)
    # =====================================
    if accion in (
        "CONSULTA_GASTO_MAYOR",
        "CONSULTA_AFECTA_PRESUPUESTO",
        "CONSULTA_CUANTO_LLEVO",
        "CONSULTA_GASTO_PERIODO",
    ):

        from services import insights_service as ins

        cuenta_id = st.session_state["cuenta_id"]

        try:

            if accion == "CONSULTA_GASTO_MAYOR":
                return ins.en_que_gasto_mas(cuenta_id)

            if accion == "CONSULTA_AFECTA_PRESUPUESTO":
                return ins.que_afecta_presupuesto(cuenta_id)

            if accion == "CONSULTA_CUANTO_LLEVO":
                return ins.cuanto_llevo(cuenta_id)

            return ins.cuanto_gaste(
                cuenta_id,
                resultado.get("periodo"),
                resultado.get("categoria"),
            )

        except Exception:

            log.exception("Falló una consulta calculada")

            return "⚠ No pude calcular eso ahora mismo. Intenta de nuevo."

    # =====================================
    # CONSEJO PERSONAL (calculado; con IA si el plan la incluye)
    # =====================================
    if accion == "CONSEJO_PERSONAL":

        return _consejo_personal(
            st.session_state["cuenta_id"],
            resultado.get("pregunta") or resultado.get("texto_original") or "",
        )

    # =====================================
    # METAS DE AHORRO (todos los planes)
    # =====================================
    if accion == "ABRIR_METAS":

        st.session_state["pagina_actual"] = (
            "Metas de ahorro"
        )

        st.session_state[
            "debug_accion"
        ] = "metas"

        st.rerun()

    if accion in ("CREAR_META", "ABONAR_META", "CONSULTAR_METAS"):

        try:

            return _accion_meta(accion, resultado)

        except ValueError as e:

            return f"⚠ {e}"

        except Exception:

            log.exception("Falló una acción de metas")

            return (
                "⚠ No pude acceder a tus metas ahora mismo. Intenta de "
                "nuevo en un momento."
            )

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

        # "me depositaron 5000 pesos": si el monto viene con unidad
        # clara, se registra directo en vez de volver a preguntarlo.
        original = resultado.get("texto_original") or ""

        if re.search(r"(\$\s*\d|\d\s*(pesos|mil)\b|\bmil\b)", original.lower()):

            monto_dicho = extraer_monto_flexible(original)

            if monto_dicho:
                return ejecutar_accion({
                    "accion": "REGISTRAR_INGRESO",
                    "concepto": "Ingreso",
                    "origen_ingreso": "Ingreso",
                    "monto": monto_dicho,
                    "texto_original": original,
                })

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

        coincidencia = _buscar_recordatorios(
            recordatorios,
            descripcion
        )

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

        coincidencia = _buscar_recordatorios(
            recordatorios,
            descripcion
        )

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