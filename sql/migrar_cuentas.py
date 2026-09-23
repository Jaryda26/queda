"""
Migración única — correr DESPUÉS de aplicar sql/schema.sql y ANTES
de desplegar el código de la fase 3 (cuentas compartidas).

Qué hace:
1. Para cada usuario que todavía no tiene cuenta_id, le crea una
   cuenta INDIVIDUAL y lo deja como ADMIN de esa cuenta.
2. "Rellena" cuenta_id en sus movimientos, presupuestos,
   recordatorios y diccionario_usuario existentes.
3. Le crea una suscripción con status='active' y plan 'individual'
   SIN datos de Stripe, para que tu propio uso actual no quede
   bloqueado por el paywall el día que despliegues esto. Bórrala o
   cámbiala por tu plan real cuando quieras (o suscríbete de verdad
   desde la pantalla de Suscripción).

Es seguro correrlo más de una vez: solo toca usuarios con
cuenta_id IS NULL, así que si ya corrió no vuelve a hacer nada.

Uso:
    python sql/migrar_cuentas.py
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from db import ejecutar_query, ejecutar_query_retornando, obtener_dataframe  # noqa: E402


def migrar():

    usuarios = obtener_dataframe(
        """
        SELECT id, nombre
        FROM gastos.usuarios
        WHERE cuenta_id IS NULL
        """
    )

    if usuarios.empty:
        print("Nada que migrar — todos los usuarios ya tienen cuenta.")
        return

    for _, usuario in usuarios.iterrows():

        usuario_id = int(usuario["id"])
        nombre = usuario["nombre"] or f"Usuario {usuario_id}"

        fila_cuenta = ejecutar_query_retornando(
            """
            INSERT INTO gastos.cuentas (nombre, tipo)
            VALUES (:nombre, 'INDIVIDUAL')
            RETURNING id
            """,
            {"nombre": f"Cuenta de {nombre}"}
        )

        cuenta_id = fila_cuenta[0]

        ejecutar_query(
            """
            UPDATE gastos.usuarios
            SET cuenta_id = :cuenta_id, rol_cuenta = 'ADMIN'
            WHERE id = :usuario_id
            """,
            {"cuenta_id": cuenta_id, "usuario_id": usuario_id}
        )

        for tabla in (
            "movimientos",
            "presupuestos",
            "recordatorios",
            "diccionario_usuario"
        ):

            ejecutar_query(
                f"""
                UPDATE gastos.{tabla}
                SET cuenta_id = :cuenta_id
                WHERE usuario_id = :usuario_id
                AND cuenta_id IS NULL
                """,
                {"cuenta_id": cuenta_id, "usuario_id": usuario_id}
            )

        plan_df = obtener_dataframe(
            "SELECT id FROM gastos.planes WHERE slug = 'individual'"
        )

        plan_id = (
            int(plan_df.iloc[0]["id"])
            if not plan_df.empty else None
        )

        ejecutar_query(
            """
            INSERT INTO gastos.suscripciones
            (cuenta_id, plan_id, status, fecha_inicio)
            VALUES
            (:cuenta_id, :plan_id, 'active', CURRENT_TIMESTAMP)
            """,
            {"cuenta_id": cuenta_id, "plan_id": plan_id}
        )

        print(
            f"✅ {nombre} (usuario {usuario_id}) → "
            f"cuenta {cuenta_id} creada y datos migrados."
        )

    print("Migración completa.")


if __name__ == "__main__":
    migrar()
