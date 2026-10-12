from db import ejecutar_query


def crear_movimiento(
    tipo,
    concepto,
    categoria,
    monto,
    usuario_id,
    cuenta_id
):

    query = """
    INSERT INTO gastos.movimientos
    (
        usuario_id,
        cuenta_id,
        tipo,
        concepto,
        categoria,
        monto
    )
    VALUES
    (
        :usuario_id,
        :cuenta_id,
        :tipo,
        :concepto,
        :categoria,
        :monto
    )
    """

    ejecutar_query(
        query,
        {
            "usuario_id": usuario_id,
            "cuenta_id": cuenta_id,
            "tipo": tipo,
            "concepto": concepto,
            "categoria": categoria,
            "monto": monto
        }
    )