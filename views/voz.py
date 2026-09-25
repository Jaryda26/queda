import tempfile
import hashlib
import re
import streamlit as st

from services.speech_service import speech_to_text
from services.intent_engine import detectar_intencion
from services.action_engine import ejecutar_accion
from services.billing_service import obtener_plan_actual

from views.asistente import interpretar_movimiento


def _extraer_monto_de_texto(texto):
    """
    Cuando la app pregunta '¿cuál fue el monto?' y la respuesta
    viene por voz, Azure Speech la transcribe como texto libre
    ('12000 pesos', '12,000', etc.) — a diferencia del Asistente
    de texto, que puede asumir que el usuario tecleó solo el
    número. Aquí sacamos el primer número que aparezca, ignorando
    comas y palabras alrededor. Regresa None si no hay ninguno.
    """

    texto_limpio = texto.replace(",", "")

    coincidencia = re.search(r"\d+(\.\d+)?", texto_limpio)

    if not coincidencia:
        return None

    try:
        return float(coincidencia.group(0))
    except ValueError:
        return None


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
        # fuera un mensaje nuevo. Este chequeo faltaba en voz (sí
        # existía en el Asistente de texto), y por eso al contestar
        # el monto por voz se registraba como gasto en vez de
        # ingreso: sin este bloque, un número suelto como "12000"
        # no matchea ninguna palabra clave y termina en la IA sin
        # contexto de que era la respuesta a un ingreso pendiente.

        if st.session_state.get(
            "esperando_monto_ingreso",
            False
        ):

            monto = _extraer_monto_de_texto(texto)

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

    except Exception as e:

        st.session_state[
            "audio_global"
        ] = None

        return {
            "tipo": "ERROR",
            "mensaje": f"❌ Error: {str(e)}"
        }