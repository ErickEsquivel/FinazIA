"""
analisis.py
-----------
Cálculos que convierten las categorías de la IA en información útil.
No dibuja nada: solo calcula. La interfaz (app.py) muestra los resultados.

  Idea 1 -> alerta_registro() y estado_presupuesto()
  Idea 2 -> analisis_hormiga()
  Idea 3 -> regla_50_30_20()
  Idea 4 -> la detección está en modelo_ia.py; aquí solo se listan los inusuales.
"""

import calendar
from datetime import date

import pandas as pd

from base_datos import CATEGORIAS_GASTO

BLOQUES_50_30_20 = {
    "Necesidades": ["Alimentación", "Transporte", "Vivienda y Servicios", "Salud y Educación"],
    "Deseos": ["Ocio y Entretenimiento", "Gastos Hormiga"],
}
IDEAL = {"Necesidades": 0.50, "Deseos": 0.30, "Ahorro": 0.20}


def pesos(valor) -> str:
    """Formatea un número como pesos colombianos: 1234567 -> $1.234.567"""
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.0f}".replace(",", ".")


def periodo_de(fecha) -> str:
    return pd.Timestamp(fecha).strftime("%Y-%m")


def filtrar_mes(df: pd.DataFrame, periodo: str) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["fecha_hora"].dt.strftime("%Y-%m") == periodo]


def resumen_mes(df_mes: pd.DataFrame) -> dict:
    ingresos = df_mes.loc[df_mes["tipo_movimiento"] == "Ingreso", "monto"].sum() if not df_mes.empty else 0
    gastos = df_mes.loc[df_mes["tipo_movimiento"] == "Gasto", "monto"].sum() if not df_mes.empty else 0
    return {"ingresos": float(ingresos), "gastos": float(gastos), "saldo": float(ingresos - gastos)}


def ingreso_referencia(df_mes, ingreso_configurado) -> float:
    """Usa los ingresos registrados en el mes; si no hay, el ingreso declarado."""
    registrados = resumen_mes(df_mes)["ingresos"]
    return registrados if registrados > 0 else float(ingreso_configurado)


def gasto_por_categoria(df_mes: pd.DataFrame) -> pd.Series:
    gastos = df_mes[df_mes["tipo_movimiento"] == "Gasto"] if not df_mes.empty else df_mes
    serie = gastos.groupby("categoria_final")["monto"].sum() if not gastos.empty else pd.Series(dtype=float)
    return serie.reindex(CATEGORIAS_GASTO, fill_value=0.0)


# ----------------------------------------------------------------------------
# Idea 1: presupuesto y alerta en el momento de registrar
# ----------------------------------------------------------------------------
def estado_presupuesto(df_mes, presupuestos: dict) -> pd.DataFrame:
    gastado = gasto_por_categoria(df_mes)
    filas = []
    for cat in CATEGORIAS_GASTO:
        limite = float(presupuestos.get(cat, 0))
        g = float(gastado.get(cat, 0))
        filas.append({
            "categoria": cat,
            "gastado": g,
            "limite": limite,
            "porcentaje": (g / limite) if limite > 0 else 0.0,
            "restante": limite - g,
        })
    return pd.DataFrame(filas)


def alerta_registro(categoria, monto, df_mes, presupuestos):
    """
    Devuelve (nivel, mensaje) para mostrar justo al registrar un gasto.
    nivel: 'ok', 'aviso' o 'peligro'.
    """
    limite = float(presupuestos.get(categoria, 0))
    if limite <= 0:
        return "ok", f"No tienes un límite definido para {categoria}."
    antes = float(gasto_por_categoria(df_mes).get(categoria, 0))
    despues = antes + float(monto)
    pct = despues / limite
    if pct > 1:
        return "peligro", (f"Con este gasto superas tu presupuesto de {categoria} por "
                           f"{pesos(despues - limite)} ({pct:.0%} del límite).")
    if pct >= 0.8:
        return "aviso", (f"Este gasto te deja en el {pct:.0%} de tu límite de {categoria}. "
                         f"Te quedan {pesos(limite - despues)} para el resto del mes.")
    return "ok", (f"Vas en el {pct:.0%} de tu límite de {categoria}. "
                  f"Te quedan {pesos(limite - despues)}.")


# ----------------------------------------------------------------------------
# Idea 2: detector de gastos hormiga
# ----------------------------------------------------------------------------
def _dias(periodo, hoy: date):
    anio, mes = map(int, periodo.split("-"))
    dias_mes = calendar.monthrange(anio, mes)[1]
    if (anio, mes) == (hoy.year, hoy.month):
        return hoy.day, dias_mes
    return dias_mes, dias_mes  # mes ya terminado (o futuro): se toma completo


def analisis_hormiga(df_mes, periodo, hoy: date, ingreso_ref) -> dict:
    hormiga = df_mes[(df_mes["categoria_final"] == "Gastos Hormiga")
                     & (df_mes["tipo_movimiento"] == "Gasto")] if not df_mes.empty else df_mes
    transcurridos, dias_mes = _dias(periodo, hoy)
    total = float(hormiga["monto"].sum()) if not hormiga.empty else 0.0
    por_dia = total / max(transcurridos, 1)
    resultado = {
        "cantidad": int(len(hormiga)),
        "total": total,
        "promedio": total / len(hormiga) if len(hormiga) else 0.0,
        "proyeccion_mes": por_dia * dias_mes,
        "proyeccion_anual": por_dia * 365,
        "pct_ingreso": (por_dia * dias_mes / ingreso_ref) if ingreso_ref > 0 else None,
        "frecuentes": [],
        "franja": None,
    }
    if not hormiga.empty:
        frecuentes = (hormiga.assign(desc=hormiga["descripcion"].str.lower().str.strip())
                      .groupby("desc")["monto"].agg(["count", "sum"])
                      .sort_values(["count", "sum"], ascending=False).head(3))
        resultado["frecuentes"] = [(d, int(r["count"]), float(r["sum"])) for d, r in frecuentes.iterrows()]
        horas = hormiga["fecha_hora"].dt.hour
        franjas = pd.cut(horas, bins=[-1, 5, 11, 13, 17, 23],
                         labels=["madrugada", "mañana", "mediodía", "tarde", "noche"])
        resultado["franja"] = str(franjas.value_counts().idxmax())
    return resultado


# ----------------------------------------------------------------------------
# Idea 3: regla 50/30/20
# ----------------------------------------------------------------------------
def regla_50_30_20(df_mes, ingreso_ref) -> dict:
    gastado = gasto_por_categoria(df_mes)
    necesidades = float(gastado[BLOQUES_50_30_20["Necesidades"]].sum())
    deseos = float(gastado[BLOQUES_50_30_20["Deseos"]].sum())
    ahorro = float(ingreso_ref - necesidades - deseos)
    montos = {"Necesidades": necesidades, "Deseos": deseos, "Ahorro": ahorro}
    bloques = {}
    for nombre, monto in montos.items():
        pct = monto / ingreso_ref if ingreso_ref > 0 else 0.0
        if nombre == "Ahorro":
            bien = pct >= IDEAL[nombre]
        else:
            bien = pct <= IDEAL[nombre]
        bloques[nombre] = {"monto": monto, "pct": pct, "ideal": IDEAL[nombre], "bien": bien}

    if ingreso_ref <= 0:
        consejo = "Registra tus ingresos o define tu ingreso mensual para calcular la regla."
    elif not bloques["Deseos"]["bien"]:
        exceso = deseos - IDEAL["Deseos"] * ingreso_ref
        consejo = (f"Tus deseos (ocio y gastos hormiga) van en {bloques['Deseos']['pct']:.0%}. "
                   f"Recortar {pesos(exceso)} te devolvería al 30% recomendado.")
    elif not bloques["Necesidades"]["bien"]:
        consejo = (f"Tus necesidades van en {bloques['Necesidades']['pct']:.0%}. Revisa si algún "
                   f"gasto fijo (arriendo, servicios, transporte) se puede reducir.")
    elif not bloques["Ahorro"]["bien"]:
        consejo = f"Vas ahorrando el {bloques['Ahorro']['pct']:.0%}; la meta es 20%."
    else:
        consejo = "Vas cumpliendo la regla 50/30/20. ¡Sigue así!"
    return {"bloques": bloques, "consejo": consejo}


# ----------------------------------------------------------------------------
# Precisión real de la IA con los datos del usuario
# ----------------------------------------------------------------------------
def precision_real(df) -> tuple:
    """Porcentaje de movimientos en que el usuario NO tuvo que cambiar la categoría."""
    if df.empty:
        return None, 0
    aciertos = (df["categoria_ia"] == df["categoria_final"]).mean()
    return float(aciertos), int(len(df))
