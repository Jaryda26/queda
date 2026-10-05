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

        /* ===== MICRÓFONO FLOTANTE =====
           El micrófono (audio_recorder_streamlit) es un paquete de
           terceros que dibuja un iframe con fondo blanco por dentro;
           eso no se puede cambiar con background-color desde afuera
           (el iframe es otro documento). Lo que sí funciona:
           invert(1) vuelve ese blanco negro, y mix-blend-mode:screen
           lo funde con el fondo verde del contenedor (screen(negro,X)
           = X), así el ícono queda sobre un círculo verde sólido. Los
           colores del ícono en app.py están calculados para ese
           proceso (verificado con las fórmulas exactas).

           El contenedor se fija con position:fixed a la ventana. Una
           regla por selector, a propósito: si un navegador no
           entiende :has(), solo se ignora esa regla y no todas.
           Ajuste fino del ícono: --mic-dx / --mic-dy. */

        :root {
            --mic-size: 84px;
            --mic-dx: 14px;
            --mic-dy: 10px;
        }

        [data-testid="stElementContainer"]:has(iframe[title*="audio_recorder"]) {
            position: fixed !important;
            right: 24px;
            bottom: 24px;
            width: var(--mic-size) !important;
            height: var(--mic-size) !important;
            min-height: 0 !important;
            z-index: 999990;
            border-radius: 50%;
            background-color: #0F3D37;
            box-shadow: 0 8px 22px rgba(15, 61, 55, 0.45);
            overflow: hidden;
            isolation: isolate;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .element-container:has(iframe[title*="audio_recorder"]) {
            position: fixed !important;
            right: 24px;
            bottom: 24px;
            width: var(--mic-size) !important;
            height: var(--mic-size) !important;
            min-height: 0 !important;
            z-index: 999990;
            border-radius: 50%;
            background-color: #0F3D37;
            box-shadow: 0 8px 22px rgba(15, 61, 55, 0.45);
            overflow: hidden;
            isolation: isolate;
        }

        [data-testid="stElementContainer"]:has(iframe[title*="audio_recorder"]):hover {
            transform: scale(1.06);
            box-shadow: 0 10px 26px rgba(15, 157, 139, 0.55);
        }

        iframe[title*="audio_recorder"] {
            display: block;
            width: var(--mic-size) !important;
            height: var(--mic-size) !important;
            filter: invert(1);
            mix-blend-mode: screen;
            transform: translate(var(--mic-dx), var(--mic-dy));
        }

        /* El reproductor de audio (st.audio) de las respuestas
           habladas es nativo, no un iframe: sus controles también
           son un widget del navegador con fondo claro. Mismo
           truco, en la barra lateral (fondo verde detrás). */

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
