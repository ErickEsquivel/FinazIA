"""Inicio: saldo del mes, acciones rápidas, gasto por categoría, presupuestos y análisis."""

import pandas as pd
import streamlit as st

import analisis as an
import base_datos as bd
from ui import componentes as ui
from ui import datos, graficos

# Frase correcta para cada franja horaria ("al mediodía", no "en la mediodía")
FRANJA = {"madrugada": "en la madrugada", "mañana": "en la mañana", "mediodía": "al mediodía",
          "tarde": "en la tarde", "noche": "en la noche"}

ui.mostrar_flash()
df = datos.movimientos()
presupuestos = bd.leer_presupuestos()
hoy = datos.ahora()

# ----------------------------------------------------------------------------
# Encabezado: mes con flechas
# ----------------------------------------------------------------------------
cab_izq, cab_der = st.columns([3, 2], vertical_alignment="bottom")
cab_izq.title("Inicio")
with cab_der:
    periodo = ui.selector_mes_flechas(df, an.periodo_de(hoy))

df_mes = an.filtrar_mes(df, periodo)
resumen = an.resumen_mes(df_mes)
ingreso_ref = an.ingreso_referencia(df_mes, bd.ingreso_mensual())

# Comparación con el mes anterior
anterior = (pd.Period(periodo, freq="M") - 1).strftime("%Y-%m")
gastos_ant = an.resumen_mes(an.filtrar_mes(df, anterior))["gastos"]
if gastos_ant > 0:
    cambio = resumen["gastos"] / gastos_ant - 1
    comparacion = f"{'▲' if cambio > 0 else '▼'} {abs(cambio):.0%} vs. {ui.nombre_mes(anterior).split()[0].lower()}"
else:
    comparacion = "Sin mes anterior para comparar"

# ----------------------------------------------------------------------------
# Tarjeta de saldo (estilo Wallet) + acciones rápidas (estilo Monefy)
# ----------------------------------------------------------------------------
saldo = resumen["saldo"]
st.html(f"""
<div class="fz-hero">
  <div class="etq">Saldo de {ui.nombre_mes(periodo).lower()}</div>
  <div class="saldo {'neg' if saldo < 0 else ''}">{an.pesos(saldo)}</div>
  <div class="fila">
    <div class="kpi"><span>↑ Ingresos</span><b>{an.pesos(resumen['ingresos'])}</b></div>
    <div class="kpi"><span>↓ Gastos</span><b>{an.pesos(resumen['gastos'])}</b><small>{comparacion}</small></div>
  </div>
</div>
""")

with st.container(horizontal=True, key="acciones"):
    if st.button("Gasto", icon=":material/remove:", type="primary", width="stretch"):
        ui.ir_a_registrar("Gasto")
    if st.button("Ingreso", icon=":material/add:", width="stretch"):
        ui.ir_a_registrar("Ingreso")

if df_mes.empty:
    with st.container(border=True, key="card_vacio"):
        ui.estado_vacio("🧾", "Todavía no hay movimientos este mes",
                        "Registra tu primer gasto o ingreso con los botones de arriba.")
    st.stop()

# ----------------------------------------------------------------------------
# Gasto por categoría + presupuestos
# ----------------------------------------------------------------------------
izq, der = st.columns(2, gap="medium")

with izq, st.container(border=True, key="card_categorias", height="stretch"):
    serie = an.gasto_por_categoria(df_mes)
    ui.titulo_tarjeta("Gastos por categoría", an.pesos(serie.sum()))
    if serie.sum() > 0:
        st.altair_chart(graficos.dona_categorias(serie), width="stretch")
        st.html(graficos.leyenda_categorias(serie))
    else:
        st.caption("Aún no hay gastos este mes.")

with der, st.container(border=True, key="card_presupuestos", height="stretch"):
    estado = an.estado_presupuesto(df_mes, presupuestos)
    superados = int((estado["porcentaje"] > 1).sum())
    ui.titulo_tarjeta("Presupuestos", f"{superados} superado{'s' if superados != 1 else ''}"
                      if superados else "Todo en orden ✓")
    estado = estado.sort_values("porcentaje", ascending=False)
    st.html("".join(ui.barra_presupuesto(f) for _, f in estado.iterrows()))
    st.page_link("vistas/presupuesto.py", label="Ajustar límites", icon=":material/tune:")

# ----------------------------------------------------------------------------
# Análisis en pestañas (evita el scroll largo)
# ----------------------------------------------------------------------------
h = an.analisis_hormiga(df_mes, periodo, hoy.date(), ingreso_ref)
regla = an.regla_50_30_20(df_mes, ingreso_ref)
inusuales = df_mes[df_mes["atipico"]]

with st.container(border=True, key="card_analisis"):
    t_evol, t_hormiga, t_regla, t_inus = st.tabs([
        ":material/show_chart: Evolución",
        f":material/pest_control: Hormiga ({h['cantidad']})",
        ":material/pie_chart: Regla 50/30/20",
        f":material/report: Inusuales ({len(inusuales)})",
    ])

    with t_evol:
        limite_total = sum(presupuestos.values())
        st.caption("Gasto acumulado del mes frente al ritmo que te permite tu presupuesto "
                   f"({an.pesos(limite_total)}).")
        st.altair_chart(graficos.evolucion_gasto(df_mes, periodo, limite_total, hoy), width="stretch")

    with t_hormiga:
        if h["cantidad"] == 0:
            ui.avisar("ok", "No tienes gastos hormiga este mes. ¡Bien!")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Llevas", an.pesos(h["total"]), f"{h['cantidad']} compras", delta_color="off", delta_arrow="off")
            c2.metric("Si sigues así, en un año", an.pesos(h["proyeccion_anual"]),
                      f"{an.pesos(h['proyeccion_mes'])} este mes", delta_color="off", delta_arrow="off")
            texto = f"En promedio gastas **{an.pesos(h['promedio'])}** cada vez"
            if h["pct_ingreso"] is not None:
                texto += f" y al ritmo actual se llevarán el **{h['pct_ingreso']:.1%}** de tu ingreso"
            texto += f". Suelen ocurrir {FRANJA.get(h['franja'], 'durante el día')}."
            st.markdown(texto)
            if h["frecuentes"]:
                st.markdown("**Los que más se repiten**")
                st.html("".join(
                    f'<div class="fz-mov" style="margin:.35rem 0">{ui.icono_redondo("Gastos Hormiga")}'
                    f'<div class="txt"><div class="desc">{ui.esc(d.capitalize())}</div>'
                    f'<div class="meta">{v} {"vez" if v == 1 else "veces"}</div></div>'
                    f'<span style="margin-left:auto">{ui.monto_html(t)}</span></div>'
                    for d, v, t in h["frecuentes"]))

    with t_regla:
        st.caption(f"Sobre un ingreso de {an.pesos(ingreso_ref)}. Necesidades: alimentación, transporte, "
                   "vivienda y salud. Deseos: ocio y gastos hormiga. Ahorro: lo que sobra.")
        filas = []
        for nombre, b in regla["bloques"].items():
            # Para Necesidades y Deseos la barra se llena hacia su tope; para Ahorro hacia su meta
            relativo = b["pct"] / b["ideal"] if b["ideal"] else 0
            if nombre == "Ahorro":
                c = ui.VERDE if b["bien"] else (ui.ROJO if b["pct"] < 0 else ui.AMBAR)
            else:
                c = ui.VERDE if b["bien"] else ui.ROJO
            estado_txt = "✓ Dentro de lo recomendado" if b["bien"] else "✗ Fuera de lo recomendado"
            filas.append(ui.barra_html(
                f"<b>{nombre}</b>", relativo,
                f'{b["pct"]:.0%} <span class="fz-muted">· ideal {b["ideal"]:.0%}</span>',
                f'{an.pesos(b["monto"])}', estado_txt, color_barra=c))
        st.html("".join(filas))
        ui.avisar("ok" if all(b["bien"] for b in regla["bloques"].values()) else "info", regla["consejo"])

    with t_inus:
        if inusuales.empty:
            ui.avisar("ok", "La IA no detectó movimientos inusuales este mes.")
        else:
            for _, m in inusuales.iterrows():
                st.html(f'<div class="fz-mov" style="margin:.5rem 0">{ui.icono_redondo(m["categoria_final"])}'
                        f'<div class="txt"><div class="desc">{ui.esc(m["descripcion"])}</div>'
                        f'<div class="meta">{m["fecha_hora"]:%d/%m %H:%M} · {ui.esc(m["motivo_atipico"] or "")}</div></div>'
                        f'<span style="margin-left:auto">{ui.monto_html(m["monto"], m["tipo_movimiento"])}</span></div>')
