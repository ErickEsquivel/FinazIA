"""
datos_demo.py
-------------
Movimientos de ejemplo para probar la app o mostrarla en la sustentación.

Representan un mes "típico" en el que cada categoría de gasto queda usada
alrededor del 50% de su límite. Para lograrlo con cualquier presupuesto:

- Los montos de GASTOS están pensados para un ingreso de $1.500.000 con los
  límites sugeridos (por ejemplo, Alimentación = 25% = $375.000 -> se gastan ~$187.500).
- Al cargarlos, los montos de cada categoría se multiplican por un factor para
  que sumen el 50% del límite que el usuario tenga guardado en ese momento.
- Los ingresos usan el ingreso mensual declarado por el usuario.

Cada movimiento pasa por la IA de verdad; la "categoría final" simula lo que
un usuario confirmaría o corregiría.
"""

from datetime import datetime, time, timedelta

import base_datos as bd

# Qué parte del límite de cada categoría se gasta en la demo
PORCENTAJE_OBJETIVO = 0.50
# Ingreso que se usa si el usuario no declaró ninguno
INGRESO_REFERENCIA = 1_500_000
# Los ejemplos van del día 1 al 28 (un mes completo)
ULTIMO_DIA = 28

# (día del mes, hora, monto base, descripción, categoría que confirmaría el usuario)
GASTOS = [
    (1, "10:00", 62_000, "recibo de energía Codensa", "Vivienda y Servicios"),
    (2, "07:40", 2_950, "pasaje Transmilenio", "Transporte"),
    (2, "10:20", 3_000, "tinto en la chaza", "Gastos Hormiga"),
    (2, "13:00", 14_000, "almuerzo corrientazo", "Alimentación"),
    (3, "15:30", 4_500, "chocoramo y gaseosa", "Gastos Hormiga"),
    (4, "08:00", 2_950, "pasaje Transmilenio", "Transporte"),
    (5, "12:30", 70_000, "mercado en el D1", "Alimentación"),
    (5, "19:00", 38_000, "recibo del agua acueducto", "Vivienda y Servicios"),
    (6, "23:40", 30_000, "cervezas con amigos", "Ocio y Entretenimiento"),
    (7, "16:45", 6_000, "empanada y jugo", "Gastos Hormiga"),
    (8, "11:00", 22_000, "consulta odontología cuota moderadora", "Salud y Educación"),
    (9, "16:20", 3_000, "tinto en la chaza", "Gastos Hormiga"),
    (10, "13:15", 15_000, "almuerzo menú del día", "Alimentación"),
    (11, "07:50", 15_000, "Uber a la universidad", "Transporte"),
    (11, "15:40", 5_000, "paquete de papas y gaseosa", "Gastos Hormiga"),
    (12, "10:30", 60_000, "compra en la tienda", "Alimentación"),  # inusual a propósito
    (12, "20:00", 27_000, "Netflix mensual", "Ocio y Entretenimiento"),
    (14, "18:30", 45_000, "plan de datos celular", "Vivienda y Servicios"),
    (15, "16:00", 4_000, "arepita con queso", "Gastos Hormiga"),
    (16, "13:00", 28_000, "domicilio almuerzo Rappi", "Alimentación"),
    (17, "15:20", 3_000, "tinto en la chaza", "Gastos Hormiga"),
    (18, "08:00", 2_950, "pasaje Transmilenio", "Transporte"),
    (19, "10:00", 15_500, "fotocopias de la universidad", "Salud y Educación"),
    (20, "19:00", 80_000, "internet del hogar", "Vivienda y Servicios"),
    (21, "19:30", 18_000, "cine con crispetas", "Ocio y Entretenimiento"),
    (22, "15:10", 2_500, "dulces chicles", "Gastos Hormiga"),
    (23, "07:45", 2_950, "pasaje Transmilenio", "Transporte"),
    (24, "16:30", 3_000, "tinto en la chaza", "Gastos Hormiga"),
    (25, "22:00", 18_000, "taxi a la casa", "Transporte"),
    (26, "09:00", 30_000, "recarga tarjeta TuLlave", "Transporte"),
    (27, "10:00", 3_000, "tinto en la chaza", "Gastos Hormiga"),
]


def _factores(presupuestos: dict) -> dict:
    """Factor por categoría para que sus gastos sumen el 50% de su límite.
    Si una categoría no tiene límite, se dejan los montos base."""
    factores = {}
    for cat in bd.CATEGORIAS_GASTO:
        base = sum(monto for _, _, monto, _, c in GASTOS if c == cat)
        limite = float(presupuestos.get(cat, 0))
        factores[cat] = PORCENTAJE_OBJETIVO * limite / base if limite > 0 and base > 0 else 1.0
    return factores


def _ingresos(ingreso: float, hoy: datetime) -> list:
    """Dos quincenas si ya pasó el día 15; si no, un solo pago por el mes completo
    (así la regla 50/30/20 no se calcula sobre medio sueldo)."""
    if hoy.day >= 15:
        mitad = round(ingreso / 2, -2)
        return [(1, "08:15", mitad, "pago de quincena"),
                (15, "08:15", ingreso - mitad, "pago de quincena")]
    # ("pago de salario del mes" se parece a ingresos pequeños del entrenamiento
    #  y la IA lo marcaba como inusual; "pago de nómina" no)
    return [(1, "08:15", ingreso, "pago de nómina")]


def movimientos_demo(hoy: datetime, ingreso: float, presupuestos: dict) -> list:
    """Lista de (fecha, monto, tipo, descripción, categoría) lista para guardar."""
    factores = _factores(presupuestos)
    filas = [(d, h, m, "Ingreso", desc, "Ingresos") for d, h, m, desc in _ingresos(ingreso, hoy)]
    filas += [(d, h, max(100, round(m * factores[c], -2)), "Gasto", desc, c)
              for d, h, m, desc, c in GASTOS]

    # Si el mes va empezando, se "comprimen" los días en los que ya pasaron
    escala = min(1.0, hoy.day / ULTIMO_DIA)
    resultado = []
    for dia, hora, monto, tipo, descripcion, categoria in filas:
        hh, mm = map(int, hora.split(":"))
        fecha = datetime.combine(hoy.date().replace(day=max(1, round(dia * escala))), time(hh, mm))
        fecha = min(fecha, hoy - timedelta(minutes=1))  # nunca en el futuro
        resultado.append((fecha, monto, tipo, descripcion, categoria))
    return resultado


def cargar_demo(motor, hoy: datetime):
    """Guarda los ejemplos en el mes actual, ajustados al presupuesto del usuario."""
    ingreso = bd.ingreso_mensual() or INGRESO_REFERENCIA
    for fecha, monto, tipo, descripcion, categoria in movimientos_demo(hoy, ingreso, bd.leer_presupuestos()):
        r = motor.predecir(fecha, monto, tipo, descripcion)
        bd.guardar_movimiento(
            fecha.strftime("%Y-%m-%d %H:%M:%S"), monto, tipo, descripcion,
            r["categoria"], r["confianza"], categoria, r["atipico"], r["motivo_atipico"],
        )
