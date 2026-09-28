import streamlit as st


def aplicar_tema():
    """
    Inyecta CSS una sola vez (llamar al inicio de app.py). Los
    selectores usan atributos data-testid de Streamlit, que son
    más estables entre versiones que las clases generadas
    automáticamente — pero si Streamlit cambia su HTML interno en
    una versión futura, en el peor caso esto deja de aplicar estilo
    (degrada con gracia) sin romper la funcionalidad de la app.
    """

    st.markdown(
        """
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, sans-serif;
        }

        /* ============ SIDEBAR ============ */

        section[data-testid="stSidebar"] {
            background-color: #0F3D37;
        }

        section[data-testid="stSidebar"] * {
            color: #EAF3F1 !important;
        }

        section[data-testid="stSidebar"] .stButton button {
            background-color: #14544B;
            border: 1px solid #1D6B60;
            color: #FFFFFF !important;
            border-radius: 10px;
            font-weight: 600;
        }

        section[data-testid="stSidebar"] .stButton button:hover {
            background-color: #1D6B60;
            border-color: #2A8577;
        }

        /* El micrófono (audio_recorder_streamlit) es un paquete de
           terceros: dibuja su iframe con fondo blanco por dentro
           (lo trae Bootstrap embebido), y eso NO se puede tocar con
           background-color desde afuera — el contenido de un
           iframe vive en su propio documento, aislado del nuestro.
           Lo único que sí atraviesa esa frontera es "filter": con
           invert(1) hue-rotate(180deg), un fondo blanco se convierte
           matemáticamente en el verde oscuro exacto de la barra
           lateral (#0F3D37) — lo calculé, no es a ojo. Los colores
           del ícono en app.py están ajustados para que, DESPUÉS de
           este filtro, se vean en el verde azulado/rojo correctos.
           Se apunta por iframe[title=...] (el nombre que Streamlit
           le da a cada componente) para no afectar el indicador de
           activación por voz, que ya tiene sus propios colores
           oscuros correctos y no necesita este truco. */

        section[data-testid="stSidebar"] iframe[title="audio_recorder"] {
            filter: invert(1) hue-rotate(180deg);
            border-radius: 12px;
        }

        /* El reproductor de audio (st.audio) de las respuestas
           habladas es nativo, no un iframe — pero sus controles
           también son un widget del navegador con fondo blanco que
           no se puede repintar con CSS normal. Mismo truco. */

        section[data-testid="stSidebar"] audio {
            filter: invert(1) hue-rotate(180deg);
            border-radius: 20px;
            width: 100%;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label {
            border-radius: 8px;
            padding: 2px 6px;
        }

        /* ============ BOTONES (área principal) ============ */

        .stButton button,
        .stLinkButton a,
        .stFormSubmitButton button {
            border-radius: 10px;
            font-weight: 600;
            transition: transform 0.12s ease, box-shadow 0.12s ease;
        }

        .stButton button:hover,
        .stLinkButton a:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(15, 157, 139, 0.25);
        }

        /* ============ TARJETAS (st.container(border=True)) ============ */

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            box-shadow: 0 1px 4px rgba(15, 61, 55, 0.08);
        }

        /* ============ MÉTRICAS ============ */

        div[data-testid="stMetric"] {
            background-color: #E6ECEB;
            border: 1px solid #D3DEDC;
            border-radius: 14px;
            padding: 16px 20px;
            height: 128px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 1px 3px rgba(15, 61, 55, 0.08);
        }

        [data-testid="stMetricLabel"] {
            color: #3E5750 !important;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            font-weight: 800;
            color: #0F9D8B;
        }

        /* ============ ALERTAS / MENSAJES ============ */

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        /* ============ INPUTS ============ */

        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTextArea textarea {
            border-radius: 10px !important;
        }

        /* ============ TÍTULOS ============ */

        h1, h2, h3 {
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        /* ============ CÓDIGO (código de invitación, etc.) ============ */

        code {
            border-radius: 8px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )
