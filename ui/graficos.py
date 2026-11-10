"""
ui/graficos.py
--------------
Gráficos con Altair. Usan el tema de Streamlit (claro/oscuro) para ejes y textos;
los colores de las categorías vienen de ui.componentes.CATEGORIA_UI.
"""

import calendar

import altair as alt
import pandas as pd

import analisis as an
from ui.componentes import CATEGORIA_UI, color, con_icono, esc
from ui.tema import PRIMARIO, ROJO


def dona_categorias(serie: pd.Series) -> alt.Chart:
    """Dona de gasto por categoría (solo categorías con gasto > 0)."""
    datos = serie[serie > 0].sort_values(ascending=False).reset_index()
    datos.columns = ["categoria", "monto"]
    datos["etiqueta"] = datos["categoria"].map(con_icono)
    datos["valor"] = datos["monto"].map(an.pesos)
    datos["porcentaje"] = datos["monto"] / datos["monto"].sum()
    dominio = list(CATEGORIA_UI)
    return (
        alt.Chart(datos)
        .mark_arc(innerRadius=62, outerRadius=100, cornerRadius=4, padAngle=0.02)
        .encode(
            theta=alt.Theta("monto:Q", stack=True),
            color=alt.Color("categoria:N", legend=None,
                            scale=alt.Scale(domain=dominio, range=[color(c) for c in dominio])),
            order=alt.Order("monto:Q", sort="descending"),
            tooltip=[alt.Tooltip("etiqueta:N", title="Categoría"),
                     alt.Tooltip("valor:N", title="Gastado"),
                     alt.Tooltip("porcentaje:Q", title="Del total", format=".0%")],
        )
        .properties(height=220)
    )


def leyenda_categorias(serie: pd.Series) -> str:
    total = serie.sum()
    filas = []
    for cat, monto in serie[serie > 0].sort_values(ascending=False).items():
        filas.append(f'<div class="it"><span class="pt" style="background:{color(cat)}"></span>'
                     f'<span>{esc(con_icono(cat))}</span>'
                     f'<span class="val"><b>{an.pesos(monto)}</b> '
                     f'<span class="fz-muted">{monto / total:.0%}</span></span></div>')
    return f'<div class="fz-leyenda">{"".join(filas)}</div>'


def evolucion_gasto(df_mes: pd.DataFrame, periodo: str, limite_total: float, hoy) -> alt.Chart:
    """Gasto acumulado día a día contra el ritmo ideal del presupuesto."""
    anio, mes = map(int, periodo.split("-"))
    dias_mes = calendar.monthrange(anio, mes)[1]
    ultimo = hoy.day if (anio, mes) == (hoy.year, hoy.month) else dias_mes

    gastos = df_mes[df_mes["tipo_movimiento"] == "Gasto"]
    por_dia = gastos.groupby(gastos["fecha_hora"].dt.day)["monto"].sum()
    real = pd.DataFrame({"dia": range(1, ultimo + 1)})
    real["monto"] = real["dia"].map(por_dia).fillna(0).cumsum()
    real["serie"] = "Gastado"

    ideal = pd.DataFrame({"dia": [1, dias_mes], "monto": [limite_total / dias_mes, limite_total]})
    ideal["serie"] = "Ritmo del presupuesto"

    datos = pd.concat([real, ideal], ignore_index=True)
    datos["valor"] = datos["monto"].map(an.pesos)

    escala = alt.Scale(domain=["Gastado", "Ritmo del presupuesto"], range=[PRIMARIO, "#8A8F98"])
    base = alt.Chart(datos).encode(
        x=alt.X("dia:Q", title="Día del mes", scale=alt.Scale(domain=[1, dias_mes]),
                axis=alt.Axis(tickMinStep=1, grid=False)),
        # Eje en pesos completos con punto de miles: $500.000
        y=alt.Y("monto:Q", title=None, axis=alt.Axis(tickCount=4, labelExpr=(
                    "'$' + join(split(format(datum.value, ',.0f'), ','), '.')"))),
        color=alt.Color("serie:N", scale=escala, legend=alt.Legend(title=None, orient="top")),
        strokeDash=alt.condition(alt.datum.serie == "Ritmo del presupuesto",
                                 alt.value([5, 4]), alt.value([1, 0])),
    )
    lineas = base.mark_line(strokeWidth=2.5, interpolate="monotone")
    hover = alt.selection_point(fields=["dia"], nearest=True, on="pointerover", empty=False)
    puntos = (base.transform_filter(alt.datum.serie == "Gastado")
              .mark_circle(size=70)
              .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)),
                      tooltip=[alt.Tooltip("dia:Q", title="Día"), alt.Tooltip("valor:N", title="Acumulado")])
              .add_params(hover))
    return (lineas + puntos).properties(height=260)


def color_saldo(valor) -> str:
    return ROJO if valor < 0 else PRIMARIO


# ----------------------------------------------------------------------------
# Gráficos de la pantalla «Modelo» (reporte de entrenamiento 70/10/20)
# ----------------------------------------------------------------------------
AZUL, NARANJA = "#2A78D6", "#EB6834"


def f1_por_k(grilla: list, peso_monto, peso_tiempo, k_elegido) -> alt.Chart:
    """F1 macro en ajuste según K, con los pesos elegidos."""
    datos = pd.DataFrame(grilla)
    datos = datos[(datos["peso_monto"] == peso_monto) & (datos["peso_tiempo"] == peso_tiempo)]
    base = alt.Chart(datos).encode(
        x=alt.X("k:O", title="K (vecinos que votan)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("f1_ajuste:Q", title="F1 macro en ajuste", axis=alt.Axis(format=".1%", tickCount=4),
                scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("k:O", title="K"), alt.Tooltip("f1_ajuste:Q", title="F1 ajuste", format=".1%"),
                 alt.Tooltip("aprende_correccion:Q", title="Aprende con 1 corrección")],
    )
    linea = base.mark_line(color=AZUL, strokeWidth=2)
    puntos = base.mark_circle(size=90).encode(
        color=alt.condition(alt.datum.k == k_elegido, alt.value(NARANJA), alt.value(AZUL)))
    return (linea + puntos).properties(height=240)


def f1_por_clase(por_clase: list) -> alt.Chart:
    datos = pd.DataFrame(por_clase)
    datos["etiqueta"] = datos["clase"].map(con_icono)
    return (
        alt.Chart(datos)
        .mark_bar(cornerRadiusEnd=4, height=16)
        .encode(
            y=alt.Y("etiqueta:N", title=None, sort="-x", axis=alt.Axis(labelLimit=180)),
            x=alt.X("f1:Q", title="F1 en la prueba", axis=alt.Axis(format=".0%", tickCount=5),
                    scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("clase:N", legend=None,
                            scale=alt.Scale(domain=list(CATEGORIA_UI), range=[color(c) for c in CATEGORIA_UI])),
            tooltip=[alt.Tooltip("etiqueta:N", title="Clase"),
                     alt.Tooltip("precision:Q", title="Precisión", format=".0%"),
                     alt.Tooltip("recall:Q", title="Recall", format=".0%"),
                     alt.Tooltip("f1:Q", title="F1", format=".0%"),
                     alt.Tooltip("soporte:Q", title="Movimientos")],
        )
        .properties(height=260)
    )


def matriz_confusion(clases: list, matriz: list) -> alt.Chart:
    filas = [{"real": clases[i], "predicha": clases[j], "n": v}
             for i, fila in enumerate(matriz) for j, v in enumerate(fila)]
    datos = pd.DataFrame(filas)
    base = alt.Chart(datos).encode(
        x=alt.X("predicha:N", title="Lo que dijo la IA", sort=clases, axis=alt.Axis(labelAngle=-35, labelLimit=110)),
        y=alt.Y("real:N", title="Categoría real", sort=clases, axis=alt.Axis(labelLimit=140)),
    )
    celdas = base.mark_rect(cornerRadius=3).encode(
        color=alt.Color("n:Q", legend=None, scale=alt.Scale(scheme="blues")),
        tooltip=[alt.Tooltip("real:N", title="Real"), alt.Tooltip("predicha:N", title="IA dijo"),
                 alt.Tooltip("n:Q", title="Movimientos")],
    )
    textos = base.mark_text(fontSize=12).encode(
        text=alt.condition(alt.datum.n > 0, "n:Q", alt.value("")),
        color=alt.condition(alt.datum.n >= max(max(f) for f in matriz) / 2, alt.value("white"), alt.value("#1A1D23")),
    )
    return (celdas + textos).properties(height=330)


def comparacion_modelos(comparacion: list) -> alt.Chart:
    filas = []
    for f in comparacion:
        filas.append({"modelo": f["modelo"], "prueba": "Prueba 20 % (frases nunca vistas)", "accuracy": f["accuracy"]})
        if "externa" in f:
            filas.append({"modelo": f["modelo"], "prueba": "Prueba externa (redactada aparte)", "accuracy": f["externa"]})
    datos = pd.DataFrame(filas)
    orden = [f["modelo"] for f in comparacion]
    return (
        alt.Chart(datos)
        .mark_bar(cornerRadiusEnd=3, height=11)
        .encode(
            y=alt.Y("modelo:N", title=None, sort=orden),
            yOffset=alt.YOffset("prueba:N"),
            x=alt.X("accuracy:Q", title="Accuracy", axis=alt.Axis(format=".0%", tickCount=5),
                    scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("prueba:N", scale=alt.Scale(range=[AZUL, NARANJA]),
                            legend=alt.Legend(title=None, orient="top", labelLimit=320)),
            tooltip=[alt.Tooltip("modelo:N", title="Modelo"), alt.Tooltip("prueba:N", title="Prueba"),
                     alt.Tooltip("accuracy:Q", title="Accuracy", format=".1%")],
        )
        .properties(height=300)
    )
