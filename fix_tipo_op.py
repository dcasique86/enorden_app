with open('tecnosport_app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''if movimiento.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        cliente = db.get_cliente_by_id(movimiento.cliente_id)'''

new = '''if movimiento.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        # Validar tipo_operacion si se proporciona
        TIPOS_OPERACION_VALIDOS = {"COMPRA", "PRESTAMO_MERCANCIA", "DEVUELTO", "PENDIENTE"}
        tipo_op_raw = movimiento.tipo_operacion
        if tipo_op_raw is not None and tipo_op_raw not in TIPOS_OPERACION_VALIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"tipo_operacion inválido: '{tipo_op_raw}'. Valores permitidos: {', '.join(sorted(TIPOS_OPERACION_VALIDOS))}"
            )

        tipo_op = tipo_op_raw or "COMPRA"

        cliente = db.get_cliente_by_id(movimiento.cliente_id)'''

if old in content:
    content = content.replace(old, new)
    with open('tecnosport_app/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('NOT FOUND')