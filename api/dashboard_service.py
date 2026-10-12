from db import obtener_dataframe


def obtener_resumen_dashboard(cuenta_id):

    return obtener_dataframe(
        """
        SELECT tipo, monto
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
          AND DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)
        """,
        {"cuenta_id": cuenta_id}
    )


def obtener_gastos_por_categoria(cuenta_id):

    return obtener_dataframe(
        """
        SELECT COALESCE(categoria, 'Otros') AS categoria,
               SUM(monto) AS total
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
          AND tipo = 'GASTO'
          AND DATE_TRUNC('month', fecha) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY COALESCE(categoria, 'Otros')
        ORDER BY total DESC
        """,
        {"cuenta_id": cuenta_id}
    )


def obtener_tendencia(cuenta_id):

    return obtener_dataframe(
        """
        SELECT TO_CHAR(fecha, 'YYYY-MM') AS mes,
               SUM(CASE WHEN tipo='INGRESO' THEN monto ELSE 0 END) AS ingresos,
               SUM(CASE WHEN tipo='GASTO'   THEN monto ELSE 0 END) AS gastos
        FROM gastos.movimientos
        WHERE cuenta_id = :cuenta_id
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
        """,
        {"cuenta_id": cuenta_id}
    )
