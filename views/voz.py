import tempfile
import hashlib
import re
import difflib
import streamlit as st

from services.speech_service import speech_to_text
from services.intent_engine import (
    detectar_intencion,
    extraer_monto_de_texto
)
from services.action_engine import ejecutar_accion
from services.billing_service import obtener_plan_actual
from services.aprendizaje_service import buscar_frase_aprendida

from views.asistente import interpretar_movimiento



def _quitar_nombre_agente(texto):
    """
    Si el texto empieza con el nombre del agente que eligió el
    usuario ("Trobi, cuánto llevo gastado"), lo quita y regresa
    solo el comando real. Si el texto es SOLO el nombre (sin nada
    más), regresa cadena vacía. Si el nombre no aparece al inicio,
    regresa el texto sin tocar — el clic + Azure Speech no exige
    decir el nombre, solo lo reconoce si está.

    La comparación es TOLERANTE, no exacta: un nombre como "Trobi"
    no es una palabra común en español, así que el reconocimiento
    de voz lo transcribe distinto cada vez ("Trovit", "Trovi",
    etc.) — si exigiéramos coincidencia exacta, casi nunca se
    reconocería a sí mismo y el mensaje se mandaría tal cual a la
    IA, que a veces "adivinaba" que era el nombre de un
    recordatorio y regresaba "No encontré Trovit". Por eso se
    compara la PRIMERA PALABRA dicha contra el nombre configurado
    por similitud (no por igualdad) y se acepta si se parecen lo
    suficiente.
    """

    nombre_agente = st.session_state.get(
        "nombre_agente",
        "Queda"
    ).strip()

    if not nombre_agente:
        return texto

    palabras = texto.strip().split()

    if not palabras:
        return texto

    primera_palabra = re.sub(
        r"[^\wáéíóúñü]",
        "",
        palabras[0],
        flags=re.IGNORECASE
    )

    similitud = difflib.SequenceMatcher(
        None,
        primera_palabra.lower(),
        nombre_agente.lower()
    ).ratio()

    if similitud < 0.6:
        return texto

    resto = " ".join(palabras[1:]).strip()
    resto = re.sub(r"^[,.:;!?]+\s*", "", resto)

    return resto


def procesar_texto_voz(texto):
    """
    Toma un texto ya transcrito (venga de Azure Speech vía audio,
    o del reconocimiento del navegador vía la activación por
    nombre) y lo procesa exactamente igual: revisa si es la
    respuesta a una pregunta de monto pendiente, si matchea alguna
    palabra clave del motor de reglas, o si hay que mandarlo a la
    IA. Centralizado aquí para que ambos caminos de entrada de voz
    compartan la misma lógica en vez de duplicarla.
    """

    texto_sin_nombre = _quitar_nombre_agente(texto)

    if texto_sin_nombre != texto:

        if not texto_sin_nombre:

            return {
                "tipo": "MENSAJE",
                "mensaje": "🎙️ Te escucho, ¿qué necesitas?"
            }

        texto = texto_sin_nombre

    st.session_state[
        "ultimo_texto_voz"
    ] = texto

    # ===================================================
    # ESPERANDO MONTO DE INGRESO
    # ===================================================
    # Si la vez pasada detectamos un ingreso sin monto (p. ej.
    # "ya cayó el águila") y preguntamos "¿cuál fue el monto?",
    # esta respuesta es la contestación a esa pregunta — NO
    # debe pasar por detectar_intencion() ni por la IA como si
    # fuera un mensaje nuevo.

    if st.session_state.get(
        "esperando_monto_ingreso",
        False
    ):

        monto = extraer_monto_de_texto(texto)

        st.session_state["audio_global"] = None

        if monto is None:

            return {
                "tipo": "ERROR",
                "mensaje": (
                    "⚠ No logré identificar el monto. Dime "
                    "solo la cantidad, por ejemplo "
                    "'12000 pesos'."
                )
            }

        resultado = {
            "accion": "REGISTRAR_INGRESO",
            "concepto": "Ingreso",
            "origen_ingreso": "Ingreso",
            "monto": monto,
            "texto_original": texto
        }

        mensaje = ejecutar_accion(
            resultado
        )

        st.session_state[
            "esperando_monto_ingreso"
        ] = False

        return {
            "tipo": "MENSAJE",
            "mensaje": mensaje
        }

    # Primero se revisa si alguna frase que el usuario enseñó en
    # 🧠 Aprendizaje aplica aquí — tiene prioridad sobre las
    # palabras clave de fábrica. Si no hay ninguna coincidencia,
    # sigue el motor de reglas normal.

    intencion = buscar_frase_aprendida(
        st.session_state["cuenta_id"],
        texto
    )

    if intencion is None:

        intencion = detectar_intencion(
            texto
        )

    if intencion:

        intencion["texto_original"] = texto

        accion = intencion.get(
            "accion",
            ""
        )

        # IMPORTANTE:
        # limpiar audio antes del rerun — cualquier acción de
        # navegación (ABRIR_*) dispara st.rerun() dentro de
        # ejecutar_accion(), lo que corta la ejecución de esta
        # función ahí mismo. Si el audio no se limpia ANTES de
        # llamar a ejecutar_accion(), las líneas de después
        # nunca corren.

        if accion.startswith("ABRIR_"):

            st.session_state[
                "audio_global"
            ] = None

            ejecutar_accion(
                intencion
            )

            return {
                "tipo": "NAVEGACION",
                "accion": accion
            }

        mensaje = ejecutar_accion(
            intencion
        )

        st.session_state[
            "audio_global"
        ] = None

        return {
            "tipo": "MENSAJE",
            "mensaje": mensaje
        }

    plan = obtener_plan_actual(
        st.session_state["cuenta_id"]
    )

    if plan is None or not plan.get("incluye_ia", True):

        st.session_state["audio_global"] = None

        return {
            "tipo": "ERROR",
            "mensaje": (
                "🔒 Registrar gastos por voz libre requiere "
                "el plan Individual o Familiar. Puedes seguir "
                "usando comandos como 'abre el dashboard' o "
                "'ya pagué [recordatorio]'."
            )
        }

    resultado = interpretar_movimiento(
        texto
    )

    resultado[
        "texto_original"
    ] = texto

    mensaje = ejecutar_accion(
        resultado
    )

    st.session_state[
        "audio_global"
    ] = None

    return {
        "tipo": "MENSAJE",
        "mensaje": mensaje
    }


def pantalla_voz():

    audio_bytes = st.session_state.get(
        "audio_global"
    )

    if not audio_bytes:
        return None

    audio_hash = hashlib.md5(
        audio_bytes
    ).hexdigest()

    if st.session_state.get(
        "ultimo_audio_hash"
    ) == audio_hash:

        return {
            "tipo": "ERROR",
            "mensaje": "⚠ Audio ya procesado."
        }

    st.session_state[
        "ultimo_audio_hash"
    ] = audio_hash

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav"
        ) as tmp:

            tmp.write(audio_bytes)

            archivo_audio = tmp.name

        texto = speech_to_text(
            archivo_audio
        )

        if not texto:

            st.session_state["audio_global"] = None

            return {
                "tipo": "ERROR",
                "mensaje": "⚠ No pude entender el audio."
            }

        return procesar_texto_voz(texto)

    except Exception as e:

        st.session_state[
            "audio_global"
        ] = None

        return {
            "tipo": "ERROR",
            "mensaje": f"❌ Error: {str(e)}"
        }