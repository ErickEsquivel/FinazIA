"""Modelo: cómo se entrenó y evaluó la IA con la división 70 / 10 / 20."""

import pandas as pd
import streamlit as st

from entrenamiento import leer_reporte
from ui import componentes as ui
from ui import graficos
from ui.tema import AMBAR, PRIMARIO

COLOR_PRUEBA = "#2A78D6"

st.title("Modelo de IA")
st.caption("Cómo se entrenó y se evaluó la IA que clasifica tus movimientos.")

r = leer_reporte()
if r is None:
    with st.container(border=True, key="card_sin_reporte"):
        ui.estado_vacio("🧪", "Aún no hay un reporte del modelo",
                        "Genéralo desde la carpeta del proyecto con: python entrenamiento.py")
    st.stop()

m, d, prueba, externa = r["modelo"], r["division"], r["prueba"], r["externa"]
pesos = m["pesos"]

# ----------------------------------------------------------------------------
# Resumen
# ----------------------------------------------------------------------------
externa_html = (f'<div class="kpi"><span>Prueba externa · {externa["filas"]} frases</span>'
                f'<b>{externa["accuracy"]:.1%}</b><small>redactadas aparte</small></div>') if externa else ""
st.html(f"""
<div class="fz-hero">
  <div class="etq">Algoritmo elegido</div>
  <div class="saldo">KNN · K = {m["k"]}</div>
  <div class="fila">
    <div class="kpi"><span>Prueba 20 % · accuracy</span><b>{prueba["accuracy"]:.1%}</b><small>frases nunca vistas</small></div>
    <div class="kpi"><span>Prueba 20 % · F1 macro</span><b>{prueba["f1"]:.1%}</b><small>promedio de las 7 clases</small></div>
    {externa_html}
  </div>
</div>
""")

# ----------------------------------------------------------------------------
# División 70 / 10 / 20
# ----------------------------------------------------------------------------
ronda = d["rondas"][0]
segmentos = [
    ("Entrenamiento", 70, PRIMARIO, f"≈{ronda['entrenamiento']} movimientos", "El modelo aprende de estos ejemplos"),
    ("Ajuste", 10, AMBAR, f"≈{ronda['ajuste']} movimientos · rota {len(d['rondas'])} veces",
     "Escoger hiperparámetros sin tocar la prueba"),
    ("Prueba", 20, COLOR_PRUEBA, f"{d['prueba']['filas']} movimientos · {d['prueba']['frases_base']} frases base",
     "Medir el resultado final una sola vez"),
]
with st.container(border=True, key="card_division"):
    ui.titulo_tarjeta("División de los datos: 70 / 10 / 20",
                      f"{d['total']} movimientos · {d['frases_base']} frases base")
    barra = "".join(f'<div style="flex:{p};background:{c};color:#fff;padding:.55rem .7rem;font-weight:650;'
                    f'white-space:nowrap;overflow:hidden">{p} %</div>' for _, p, c, _, _ in segmentos)
    leyenda = "".join(
        f'<div style="flex:1 1 180px"><div style="display:flex;align-items:center;gap:.45rem;font-weight:650">'
        f'<span class="pt" style="width:10px;height:10px;border-radius:3px;background:{c}"></span>{n} · {p} %</div>'
        f'<div class="fz-muted">{cant}</div><div style="font-size:.88rem">{para}</div></div>'
        for n, p, c, cant, para in segmentos)
    st.html(f'<div style="display:flex;border-radius:.6rem;overflow:hidden;margin:.2rem 0 .9rem">{barra}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:1rem">{leyenda}</div>')
    if d["fuga"]:
        ui.avisar("peligro", "Hay frases base de la prueba que también aparecen al entrenar.")
    else:
        ui.avisar("ok", "Ninguna frase de la prueba aparece en entrenamiento ni en ajuste: la prueba mide "
                        "si la IA generaliza, no si memoriza.")
    st.markdown(
        "- **Agrupada por frase base:** todas las variantes de una frase (*«tinto con nequi»*, *«tinto hoy»*) "
        "quedan en el mismo conjunto. Con una división aleatoria, 9 de cada 10 movimientos de prueba tenían "
        "una frase «hermana» en el entrenamiento y el resultado salía inflado (≈96 %).\n"
        "- **Estratificada por clase:** cada conjunto tiene las 7 categorías.\n"
        f"- **El 10 % de ajuste rota:** un solo 10 % son ≈70 filas, muy poco para decidir. Dentro del 80 % de "
        f"desarrollo se repite la división 70/10 **{len(d['rondas'])} veces** y se promedia.")
    with st.expander("Ver las rondas de ajuste"):
        st.dataframe(pd.DataFrame([{"Ronda": i + 1, "Entrenamiento (70 %)": rd["entrenamiento"],
                                    "Ajuste (10 %)": rd["ajuste"]} for i, rd in enumerate(d["rondas"])]),
                     hide_index=True, width="stretch")

# ----------------------------------------------------------------------------
# Detalle por etapa
# ----------------------------------------------------------------------------
with st.container(border=True, key="card_etapas"):
    t_ajuste, t_prueba, t_comp, t_conf = st.tabs([
        ":material/tune: Ajuste (10 %)", ":material/fact_check: Prueba (20 %)",
        ":material/leaderboard: Comparación", ":material/verified: Confianza",
    ])

    with t_ajuste:
        aj = r["ajuste"]
        st.markdown(f"Métrica para escoger: **{aj['metrica']}**. Se probaron "
                    f"**{len(aj['grilla_knn'])} configuraciones** de KNN (K y peso del monto y la hora).")
        st.altair_chart(graficos.f1_por_k(aj["grilla_knn"], pesos["numero"], pesos["tiempo"], m["k"]),
                        width="stretch")
        st.caption(f"Con los pesos elegidos (monto {pesos['numero']:g}, tiempo {pesos['tiempo']:g}). "
                   "El punto naranja es el K del modelo.")
        st.markdown(
            f"**Elegido:** K = {m['k']}, `weights = {m['weights']}`, distancia {m['metric']}, pesos por bloque "
            f"texto {pesos['texto']:g} · tipo {pesos['tipo']:g} · monto {pesos['numero']:g} · tiempo {pesos['tiempo']:g} "
            f"(F1 en ajuste {m['f1_ajuste']:.1%}).\n\n"
            "Además del F1, la app necesita **aprender de una sola corrección** del usuario: los pesos se "
            f"escogen entre las configuraciones que aciertan las {aj['total_correcciones']} pruebas de corrección, "
            "y se deja K = 5 porque es más estable a medida que crecen los datos de cada usuario.")
        mejores = (pd.DataFrame(aj["grilla_knn"]).sort_values("f1_ajuste", ascending=False).head(8)
                   .rename(columns={"k": "K", "peso_monto": "Peso monto", "peso_tiempo": "Peso tiempo",
                                    "f1_ajuste": "F1 ajuste", "aprende_correccion": "Aprende con 1 corrección"}))
        st.dataframe(mejores, hide_index=True, width="stretch",
                     column_config={"F1 ajuste": st.column_config.NumberColumn(format="percent")})

    with t_prueba:
        st.markdown("El modelo elegido se entrena con el 80 % de desarrollo (70 % + 10 %) y se evalúa **una sola "
                    "vez** en el 20 % de prueba.")
        with st.container(horizontal=True):
            for etiqueta, clave, ayuda in [("Accuracy", "accuracy", "Movimientos bien clasificados"),
                                           ("Error", "error", "1 − accuracy (MAE con pérdida 0-1)"),
                                           ("Precisión", "precision", "Promedio macro de las 7 clases"),
                                           ("Recall", "recall", "Promedio macro de las 7 clases"),
                                           ("F1 macro", "f1", "Media armónica de precisión y recall")]:
                st.metric(etiqueta, f"{prueba[clave]:.1%}", help=ayuda, border=True)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            ui.titulo_tarjeta("F1 por categoría")
            st.altair_chart(graficos.f1_por_clase(prueba["por_clase"]), width="stretch")
        with c2:
            ui.titulo_tarjeta("Matriz de confusión")
            st.altair_chart(graficos.matriz_confusion(prueba["clases"], prueba["matriz"]), width="stretch")
        with st.expander("Ver la tabla por categoría"):
            st.dataframe(pd.DataFrame(prueba["por_clase"]).rename(columns={
                "clase": "Categoría", "precision": "Precisión", "recall": "Recall", "f1": "F1", "soporte": "Movimientos"}),
                hide_index=True, width="stretch",
                column_config={c: st.column_config.NumberColumn(format="percent") for c in ["Precisión", "Recall", "F1"]})

    with t_comp:
        if not r["comparacion"]:
            st.info("El reporte se generó con --rapido, sin comparar otros algoritmos.")
        else:
            st.markdown("Los 5 algoritmos se ajustaron con las mismas 8 rondas y se probaron con el mismo 20 %.")
            st.altair_chart(graficos.comparacion_modelos(r["comparacion"]), width="stretch")
            tabla = pd.DataFrame([{
                "Modelo": f["modelo"], "F1 ajuste": f["f1_ajuste"], "Prueba 20 %": f["accuracy"],
                "Prueba externa": f.get("externa"), "F1 prueba": f["f1"],
                "Aprende con 1 corrección": f"{f['aprende_correccion']} / {r['ajuste']['total_correcciones']}",
                "Hiperparámetros": ", ".join(f"{k}={v}" for k, v in f["hiperparametros"].items()),
            } for f in r["comparacion"]])
            st.dataframe(tabla, hide_index=True, width="stretch", column_config={
                c: st.column_config.NumberColumn(format="percent")
                for c in ["F1 ajuste", "Prueba 20 %", "Prueba externa", "F1 prueba"]})
            st.caption("Random Forest gana en la prueba interna porque aprende los rangos de monto y hora que se "
                       "usaron al construir el dataset; con frases redactadas aparte y al aprender de las "
                       "correcciones, KNN se comporta mejor para la app. El análisis completo está en el notebook.")

    with t_conf:
        c = prueba["confianza"]
        st.markdown(f"La app solo propone la categoría sin preguntar cuando la confianza es de al menos "
                    f"**{c['umbral']:.0%}**. En la prueba (20 %):")
        with st.container(horizontal=True):
            st.metric(f"Confianza ≥ {c['umbral']:.0%}", f"{c['acierto_alta']:.0%} de aciertos",
                      f"{c['pct_alta']:.0%} de los movimientos", delta_color="off", delta_arrow="off", border=True)
            st.metric(f"Confianza < {c['umbral']:.0%}", f"{c['acierto_baja']:.0%} de aciertos",
                      f"{c['pct_baja']:.0%} de los movimientos", delta_color="off", delta_arrow="off", border=True)
        st.markdown("Cuando la IA está segura acierta mucho más que cuando duda; por eso, si la confianza es baja, "
                    "la app te pide que elijas la categoría.")

# ----------------------------------------------------------------------------
with st.container(border=True, key="card_reentrenar"):
    ui.titulo_tarjeta("Volver a entrenar", f"Reporte del {r['generado']} · scikit-learn {r['scikit_learn']}")
    st.markdown("Desde la carpeta del proyecto (tarda unos 2 minutos):")
    st.code("python entrenamiento.py                    # evalúa y actualiza este reporte\n"
            "python entrenamiento.py --guardar-modelo   # además reemplaza el modelo de la app",
            language="bash")
    st.caption("El análisis completo, con gráficos y la justificación de cada decisión, está en "
               "notebooks/FinanzIA_analisis_modelo.ipynb.")
