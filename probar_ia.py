"""
Diagnóstico de la IA (Azure OpenAI) para la API. NO imprime tus llaves.

Uso (desde la carpeta del proyecto):
    python probar_ia.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

print("== Variables en el .env ==")

for nombre in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_DEPLOYMENT"):

    v = os.getenv(nombre)

    if v is None:
        print(f"{nombre}: NO EXISTE")
        continue

    problemas = []
    if v != v.strip():
        problemas.append("tiene espacios al inicio/final")
    if "\n" in v or "\r" in v:
        problemas.append("tiene salto de línea DENTRO")
    if v.startswith(('"', "'")) or v.endswith(('"', "'")):
        problemas.append("conserva comillas")
    if " " in v.strip():
        problemas.append("tiene espacios en medio")

    if nombre == "AZURE_OPENAI_KEY":
        detalle = f"longitud={len(v)}"
    elif nombre == "AZURE_OPENAI_ENDPOINT":
        detalle = f"{v[:40]}...{v[-14:]}  (longitud={len(v)})"
    else:
        detalle = v

    print(f"{nombre}: {detalle}", "| PROBLEMAS: " + ", ".join(problemas) if problemas else "| ok")

print("\n== Prueba real ==")

try:
    from openai import OpenAI

    cliente = OpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"].strip(),
        api_key=os.environ["AZURE_OPENAI_KEY"].strip(),
    )

    r = cliente.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"].strip(),
        messages=[{"role": "user", "content": "Responde solo: ok"}],
        max_tokens=5,
    )

    print("FUNCIONA ->", r.choices[0].message.content)

except Exception as e:
    print("FALLÓ ->", type(e).__name__)
    print(str(e)[:400])
    sys.exit(1)
