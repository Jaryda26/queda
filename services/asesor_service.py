"""
Asesor financiero con IA (web voz, chat del celular). Solo REDACTA: todas
las cifras salen de insights_service.contexto_financiero (calculadas en
Python). El cupo diario lo cobra quien llama (plan_ia_service).
"""

import json
import logging

log = logging.getLogger("queda.asesor")

PROMPT_SISTEMA = (
    "Eres el asesor financiero personal de Queda. Hablas con el usuario "
    "por texto o voz. Te doy un JSON con SUS números reales (periodo "
    "calendario, presupuesto, ingresos, resultado, categorías con su "
    "porcentaje del ingreso, gasto por día de la semana, últimos meses, "
    "metas) y su pregunta.\n\n"
    "Reglas:\n"
    "- Usa ÚNICAMENTE cifras del contexto; nunca inventes montos ni "
    "rendimientos.\n"
    "- Sé específico y personal: nombra sus categorías y montos, y da 2 o "
    "3 acciones concretas para esta semana o este periodo.\n"
    "- Si tiene metas de ahorro, calcula/usa lo que falta y conecta el "
    "consejo (qué categoría recortar para llegar).\n"
    "- Si pregunta si puede invertir: primero revisa si le sobra dinero "
    "de forma constante (resultado del periodo y meses anteriores), si "
    "tiene deudas (categoría Deudas) y si tiene un fondo de emergencia "
    "(meta). Orienta de forma educativa (fondo de emergencia, pagar "
    "deudas caras, CETES, fondos indexados) sin prometer rendimientos ni "
    "recomendar un producto específico, y aclara en una frase que no es "
    "asesoría financiera regulada.\n"
    "- Si faltan datos, dilo y sugiere registrar más movimientos.\n"
    "- Español de México, tono cálido y directo, prosa corrida: sin "
    "listas, tablas, markdown ni asteriscos.\n"
    "- Máximo 7 líneas."
)


def asesor_ia(cuenta_id, pregunta, historial=None):
    """
    Regresa el texto de la IA. Lanza excepción si la IA falla (el que
    llama devuelve el cupo y usa la respuesta calculada).
    historial: [{"rol": "usuario"|"asistente", "texto": "..."}] (opcional).
    """

    from services import insights_service as ins
    from services.ai_client import get_deployment, get_openai_client

    contexto = ins.contexto_financiero(cuenta_id)

    mensajes = [{"role": "system", "content": PROMPT_SISTEMA}]

    for h in (historial or [])[-6:]:
        texto = str(h.get("texto") or "")[:600]
        if not texto:
            continue
        mensajes.append({
            "role": "user" if h.get("rol") == "usuario" else "assistant",
            "content": texto,
        })

    mensajes.append({
        "role": "user",
        "content": (
            "Contexto: "
            + json.dumps(contexto, ensure_ascii=False, default=str)
            + "\n\nPregunta: "
            + ((pregunta or "").strip()
               or "Dame un consejo para mejorar mis finanzas")
        ),
    })

    response = get_openai_client().chat.completions.create(
        model=get_deployment(),
        messages=mensajes,
        temperature=0.4,
        max_tokens=450,
    )

    texto = (response.choices[0].message.content or "").strip()
    texto = texto.replace("`", "").replace("**", "").replace("*", "")

    if not texto:
        raise RuntimeError("respuesta vacía")

    return texto


def respuesta_calculada(cuenta_id, pregunta):
    """Sin IA: diagnóstico del periodo si preguntan por 'cómo voy / finanzas',
    si no los consejos calculados."""

    from services import insights_service as ins
    from services.intent_engine import normalizar_texto

    t = normalizar_texto(pregunta or "")

    if any(p in t for p in ("finanzas", "como voy", "como me va", "diagnostico")):
        return ins.resumen_periodo(cuenta_id)

    return ins.consejo_texto(cuenta_id)
