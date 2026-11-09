"""
datos_demo.py
-------------
Movimientos de ejemplo para probar la app o mostrarla en la sustentación.
Cada movimiento pasa por la IA de verdad; la "categoría final" simula lo que
un usuario confirmaría o corregiría.
"""

from datetime import datetime, time

import base_datos as bd

# (día del mes, hora, monto, tipo, descripción, categoría que confirmaría el usuario)
EJEMPLOS = [
    (1, "08:15", 1_400_000, "Ingreso", "pago de quincena", "Ingresos"),
    (1, "09:00", 420_000, "Gasto", "arriendo habitación", "Vivienda y Servicios"),
    (2, "07:40", 2_950, "Gasto", "pasaje Transmilenio", "Transporte"),
    (2, "10:20", 3_500, "Gasto", "tinto en la chaza", "Gastos Hormiga"),
    (2, "13:00", 15_000, "Gasto", "almuerzo corrientazo", "Alimentación"),
    (3, "15:30", 4_500, "Gasto", "chocoramo y gaseosa", "Gastos Hormiga"),
    (3, "18:10", 85_000, "Gasto", "recibo de energía Codensa", "Vivienda y Servicios"),
    (4, "08:00", 2_950, "Gasto", "pasaje Transmilenio", "Transporte"),
    (4, "16:00", 3_000, "Gasto", "tinto en la chaza", "Gastos Hormiga"),
    (5, "12:30", 180_000, "Gasto", "mercado en el D1", "Alimentación"),
    (5, "23:40", 60_000, "Gasto", "cervezas con amigos", "Ocio y Entretenimiento"),
    (6, "01:30", 35_000, "Gasto", "cover en la discoteca", "Ocio y Entretenimiento"),
    (6, "16:45", 6_000, "Gasto", "empanada y jugo", "Gastos Hormiga"),
    (7, "19:00", 32_000, "Gasto", "cine con crispetas", "Ocio y Entretenimiento"),
    (8, "15:10", 2_500, "Gasto", "dulces chicles", "Gastos Hormiga"),
    (9, "11:00", 45_000, "Gasto", "consulta odontología cuota moderadora", "Salud y Educación"),
    (9, "16:20", 3_500, "Gasto", "tinto en la chaza", "Gastos Hormiga"),
    (10, "13:15", 16_000, "Gasto", "almuerzo menú del día", "Alimentación"),
    (11, "07:50", 12_000, "Gasto", "Uber a la universidad", "Transporte"),
    (11, "15:40", 5_000, "Gasto", "paquete de papas y gaseosa", "Gastos Hormiga"),
    (12, "20:00", 22_000, "Gasto", "Netflix mensual", "Ocio y Entretenimiento"),
    (12, "10:30", 180_000, "Gasto", "compra en la tienda", "Alimentación"),  # inusual a propósito
    (13, "16:10", 3_500, "Gasto", "tinto en la chaza", "Gastos Hormiga"),
    (14, "18:30", 48_000, "Gasto", "plan de datos celular", "Vivienda y Servicios"),
    (15, "08:15", 1_400_000, "Ingreso", "pago de quincena", "Ingresos"),
    (15, "16:00", 4_000, "Gasto", "arepita con queso", "Gastos Hormiga"),
    (16, "13:00", 25_000, "Gasto", "domicilio almuerzo Rappi", "Alimentación"),
    (17, "15:20", 3_000, "Gasto", "tinto en la chaza", "Gastos Hormiga"),
]


def cargar_demo(motor, hoy: datetime):
    """Guarda los ejemplos en el mes actual. Si el mes va empezando, los
    "comprime" en los días que ya pasaron para que no queden fechas futuras."""
    escala = min(1.0, hoy.day / 17)
    for dia, hora, monto, tipo, descripcion, categoria in EJEMPLOS:
        if dia == 15 and tipo == "Ingreso" and hoy.day < 15:
            continue  # la segunda quincena todavía no ha llegado
        dia_real = max(1, round(dia * escala))
        hh, mm = map(int, hora.split(":"))
        fecha = datetime.combine(hoy.date().replace(day=dia_real), time(hh, mm))
        r = motor.predecir(fecha, monto, tipo, descripcion)
        bd.guardar_movimiento(
            fecha.strftime("%Y-%m-%d %H:%M:%S"), monto, tipo, descripcion,
            r["categoria"], r["confianza"], categoria, r["atipico"], r["motivo_atipico"],
        )
