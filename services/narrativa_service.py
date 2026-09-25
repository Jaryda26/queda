import json
from datetime import date

from db import obtener_dataframe
from services.ai_client import get_openai_client, get_deployment


PROMPT_NARRATIVA = """
Eres el asistente financiero de la app "Queda". Vas a redactar un
mensaje breve de bienvenida (máximo 4 líneas, sin saludo inicial:
el saludo ya lo pone la app aparte) a partir de un JSON con datos
financieros reales del usuario.

Reglas estrictas:
- Usa ÚNICAMENTE las cifras que vienen en el JSON. No inventes,
  no cambies, no agregues ninguna cifra que no esté ahí.
- Si "proyeccion_fin_periodo" o "proyeccion_proximo_recordatorio"
  son positivos, es una proyección de AHORRO/margen. Si son
  negativos, es una proyección de DÉFICIT (les va a faltar dinero).
- Tono cálido y motivador cuando las proyecciones son buenas; tono
  de alerta amable (nunca alarmista, nunca culpabilizador) cuando
  son malas.
- Si "proximo_recordatorio" no es null, menciónalo por su
  descripción y en cuántos días vence.
- Si no hay presupuesto activo ("proyeccion_fin_periodo" es null),
  invita amablemente a configurar uno, sin inventar cifras.
- Español de México, cercano, natural. Sin tecnicismos financieros,
  sin markdown, sin listas — solo el mensaje en prosa corrida.
- PROHIBIDO usar backticks (`), asteriscos (*) o cualquier símbolo
  de formato — ni siquiera para resaltar montos. Escribe los montos
  como texto plano, por ejemplo: $7,101 o $4,333.40.
"""


def _sumar(query, params):

    df = obtener_dataframe(query, params)

    if df.empty:
        return 0.0

    valor = df.iloc[0, 0]

    return float(valor) if valor is not None else 0.0


def calcular_datos_proyeccion(cuenta_id):
    """
    Calcula, en Python puro (sin IA), los datos financieros que
    alimentan el mensaje de bienvenida: estos números son la fuente
    de verdad — la IA solo los redacta, nunca los calcula.
    """

    hoy = date.today()

    datos = {
        "disponible_actual": 0.0,
        "porcentaje_usado_presupuesto": None,
        "dias_restantes_periodo": None,
        "proyeccion_fin_periodo": None,
        "recordatorios_pendientes": 0,
        "proximo_recordatorio": None,
        "proyeccion_proximo_recordatorio": None
    }

    ingresos = _sumar(
        """
        SELECT COALESCE(SUM(monto),0)
        FROM gastos.movimientos
        WHERE tipo='INGRESO' AND cuenta_id = :cuenta_id
        """,
        {"cuenta_id": cuenta_id}
    )

    gastos_totales = _sumar(
        """
        SELECT COALESCE(SUM(monto),0)
        FROM gastos.movimientos
        WHERE tipo='GASTO' AND cuenta_id = :cuenta_id
        """,
        {"cuenta_id": cuenta_id}
    )

    datos["disponible_actual"] = round(
        ingresos - gastos_totales, 2
    )

    presupuesto_df = obtener_dataframe(
        """
        SELECT monto, fecha_inicio, fecha_fin
        FROM gastos.presupuestos
        WHERE cuenta_id = :cuenta_id
        ORDER BY id DESC
        LIMIT 1
        """,
        {"cuenta_id": cuenta_id}
    )

    if not presupuesto_df.empty:

        monto_presupuesto = float(
            presupuesto_df.iloc[0]["monto"]
        )

        fecha_inicio = presupuesto_df.iloc[0]["fecha_inicio"]
        fecha_fin = presupuesto_df.iloc[0]["fecha_fin"]

        gasto_periodo = _sumar(
            """
            SELECT COALESCE(SUM(monto),0)
            FROM gastos.movimientos
            WHERE tipo='GASTO' AND cuenta_id = :cuenta_id
            AND fecha::date BETWEEN :inicio AND :fin
            """,
            {
                "cuenta_id": cuenta_id,
                "inicio": fecha_inicio,
                "fin": fecha_fin
            }
        )

        if monto_presupuesto > 0:

            datos["porcentaje_usado_presupuesto"] = round(
                gasto_periodo / monto_presupuesto * 100, 1
            )

        dias_transcurridos = max(
            (hoy - fecha_inicio).days, 1
        )

        dias_totales = max(
            (fecha_fin - fecha_inicio).days, 1
        )

        dias_restantes = max(
            (fecha_fin - hoy).days, 0
        )

        ritmo_diario = gasto_periodo / dias_transcurridos

        datos["dias_restantes_periodo"] = dias_restantes

        datos["proyeccion_fin_periodo"] = round(
            monto_presupuesto - (ritmo_diario * dias_totales),
            2
        )

        recordatorios_df = obtener_dataframe(
            """
            SELECT descripcion, monto, fecha_vencimiento
            FROM gastos.recordatorios
            WHERE cuenta_id = :cuenta_id AND pagado = FALSE
            ORDER BY fecha_vencimiento
            """,
            {"cuenta_id": cuenta_id}
        )

        datos["recordatorios_pendientes"] = len(recordatorios_df)

        if not recordatorios_df.empty:

            row = recordatorios_df.iloc[0]
            fecha_recordatorio = row["fecha_vencimiento"]

            dias_para_recordatorio = (
                fecha_recordatorio - hoy
            ).days

            datos["proximo_recordatorio"] = {
                "descripcion": str(
                    row["descripcion"]
                ).strip().capitalize(),
                "monto": float(row["monto"]),
                "dias_restantes": dias_para_recordatorio
            }

            if (
                fecha_recordatorio <= fecha_fin
                and dias_para_recordatorio >= 0
            ):

                dias_desde_inicio = (
                    fecha_recordatorio - fecha_inicio
                ).days

                gasto_proyectado = (
                    ritmo_diario * dias_desde_inicio
                )

                datos["proyeccion_proximo_recordatorio"] = round(
                    monto_presupuesto
                    - gasto_proyectado
                    - float(row["monto"]),
                    2
                )

    return datos


def _narrativa_plantilla(datos):
    """
    Fallback determinista (sin IA): usa los mismos datos calculados
    arriba, redactados con plantillas. Se usa si la IA no está
    disponible o falla, para que el saludo nunca se caiga.
    """

    partes = []

    proyeccion_fin = datos["proyeccion_fin_periodo"]

    if proyeccion_fin is None:

        partes.append(
            "Todavía no tienes un presupuesto activo — "
            "configura uno para ver proyecciones de tu ritmo de gasto."
        )

    elif proyeccion_fin >= 0:

        partes.append(
            f"Vas bien: si mantienes tu ritmo actual, "
            f"cierras el periodo con ${proyeccion_fin:,.0f} de margen."
        )

    else:

        partes.append(
            f"Cuidado: a tu ritmo actual cerrarías el periodo "
            f"${abs(proyeccion_fin):,.0f} arriba de tu presupuesto."
        )

    recordatorio = datos["proximo_recordatorio"]

    if recordatorio:

        dias = recordatorio["dias_restantes"]

        if dias < 0:
            cuando = f"hace {abs(dias)} día(s)"
        elif dias == 0:
            cuando = "hoy"
        elif dias == 1:
            cuando = "mañana"
        else:
            cuando = f"en {dias} días"

        partes.append(
            f"Tu próximo pendiente es {recordatorio['descripcion']} "
            f"(${recordatorio['monto']:,.0f}), vence {cuando}."
        )

        proyeccion_recordatorio = (
            datos["proyeccion_proximo_recordatorio"]
        )

        if proyeccion_recordatorio is not None:

            if proyeccion_recordatorio >= 0:

                partes.append(
                    f"Si sigues así, para entonces te sobrarían "
                    f"${proyeccion_recordatorio:,.0f}."
                )

            else:

                partes.append(
                    f"Si sigues así, te faltarían "
                    f"${abs(proyeccion_recordatorio):,.0f} para cubrirlo."
                )

    return " ".join(partes)


def _limpiar_formato(texto):
    """
    Red de seguridad: aunque el prompt prohíbe backticks/asteriscos,
    a veces la IA los mete de todos modos (se ha visto en producción)
    y se ven feos al renderizarse como código en st.success(). Los
    quitamos a la fuerza en vez de confiar solo en la instrucción.
    """

    return (
        texto
        .replace("`", "")
        .replace("**", "")
        .replace("*", "")
        .strip()
    )


def escapar_para_markdown(texto):
    """
    st.success()/st.markdown() interpretan cualquier texto entre
    dos signos $ como fórmula LaTeX — con varios montos en el
    mismo mensaje ("$7,101 ... $4,333 ... $1,300"), todo lo que
    queda ENTRE el primer y el segundo $ se renderiza como
    ecuación, con otra tipografía. Escapamos el $ como \\$ (así
    se ve como texto plano) — SOLO para mostrarlo en pantalla.

    NO uses el resultado de esto para texto_a_voz(): Azure Speech
    lee la barra invertida en voz alta ("barra invertida"), lo que
    rompe el audio justo antes de cada monto. generar_narrativa_ia()
    regresa el texto limpio (sin escapar) exactamente por esto —
    ese es el que va a texto_a_voz(), y este escapado es solo para
    st.success()/st.markdown().
    """

    return texto.replace("$", "\\$")


def generar_narrativa_ia(cuenta_id, usar_ia=True, datos=None):
    """
    Genera el mensaje del día: los datos se calculan siempre en
    Python (fuente de verdad, cero riesgo de cifras inventadas).
    Si ya los calculaste antes en el caller (p. ej. para mostrar
    métricas en pantalla), pásalos en "datos" para no repetir las
    mismas consultas a la base.

    Si usar_ia=True, se le pide a la IA que los redacte con buen
    tono; si falla por cualquier motivo (sin credenciales, sin
    internet, cuota agotada, etc.) o si usar_ia=False (plan Básico,
    que no incluye IA), regresa la versión con plantillas usando
    los mismos datos — el saludo nunca se cae.

    Regresa el texto SIN escapar — listo para texto_a_voz(). Para
    mostrarlo en pantalla con st.success()/st.markdown(), pásalo
    primero por escapar_para_markdown().
    """

    if datos is None:
        datos = calcular_datos_proyeccion(cuenta_id)

    resultado = None

    if usar_ia:

        try:

            client = get_openai_client()
            deployment = get_deployment()

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {
                        "role": "system",
                        "content": PROMPT_NARRATIVA
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            datos,
                            ensure_ascii=False,
                            default=str
                        )
                    }
                ],
                temperature=0.4,
                max_tokens=220
            )

            texto = response.choices[0].message.content.strip()

            if texto:
                resultado = _limpiar_formato(texto)

        except Exception:
            pass

    if resultado is None:
        resultado = _narrativa_plantilla(datos)

    return resultado
