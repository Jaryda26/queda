import tempfile
import hashlib
import streamlit as st

from services.speech_service import speech_to_text
from services.intent_engine import detectar_intencion
from services.action_engine import ejecutar_accion
from services.billing_service import obtener_plan_actual

from views.asistente import interpretar_movimiento


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