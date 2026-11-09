"""
app.py
------
Interfaz de FinanzIA hecha con Streamlit.

Para ejecutarla en tu computador:
    streamlit run app.py

Pantallas:
  - Bienvenida (solo la primera vez): ingreso mensual y límites por categoría.
  - Panel: resumen del mes, presupuesto, gastos hormiga, regla 50/30/20 e inusuales.
  - Registrar movimiento: la IA clasifica, explica y alerta.
  - Historial: ver, corregir (la IA aprende) y borrar movimientos.
  - Presupuesto: cambiar límites y reiniciar el prototipo.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import analisis as an
import base_datos as bd
from datos_demo import cargar_demo
from modelo_ia import MotorIA, cargar_pipeline

RUTA_MODELO = Path(__file__).parent / "ia_clasificadora_multivariable_knn.pkl"
ZONA = ZoneInfo("America/Bogota")

st.set_page_config(page_title="FinanzIA", page_icon="💰", layout="wide")


def ahora():
    """Fecha y hora de Colombia (el servidor de Streamlit Cloud está en otra zona)."""
    return datetime.now(ZONA).replace(tzinfo=None)


# ----------------------------------------------------------------------------
# Carga del modelo: se hace UNA sola vez gracias a @st.cache_resource.
# Sin esto, Streamlit volvería a cargarlo con cada clic.
# ----------------------------------------------------------------------------
@st.cache_resource
def obtener_motor():
    return MotorIA(cargar_pipeline(RUTA_MODELO))


bd.crear_tablas()
motor = obtener_motor()
movimientos = bd.leer_movimientos()
motor.aprender(movimientos, bd.version_datos())  # aprende de lo nuevo, si hay algo nuevo


# ============================================================================
# Pantalla de bienvenida (primer ingreso)
# ============================================================================
def pantalla_bienvenida():
    st.title("Bienvenido a FinanzIA")
    st.write("Antes de empezar, cuéntanos cuánto recibes al mes. Con eso te proponemos "
             "un límite para cada categoría. Puedes cambiarlos cuando quieras.")

    ingreso = st.number_input("¿Cuánto recibes al mes, aproximadamente? ($ COP)",
                              min_value=0, step=50_000, value=1_500_000)

    with st.form("bienvenida"):
        st.subheader("Límite mensual por categoría")
        columnas = st.columns(3)
        limites = {}
        for i, cat in enumerate(bd.CATEGORIAS_GASTO):
            sugerido = int(round(ingreso * bd.PORCENTAJE_SUGERIDO[cat], -3))
            limites[cat] = columnas[i % 3].number_input(cat, min_value=0, step=10_000, value=sugerido)
        st.caption(f"Total asignado: {an.pesos(sum(limites.values()))} de {an.pesos(ingreso)}. "
                   "Lo que no asignes queda como ahorro.")
        demo = st.checkbox("Cargar movimientos de ejemplo para probar la app", value=True)
        if st.form_submit_button("Empezar", type="primary"):
            bd.guardar_config("ingreso_mensual", ingreso)
            bd.guardar_presupuestos(limites)
            bd.guardar_config("configurado", "si")
            if demo:
                cargar_demo(motor, ahora())
            st.rerun()


# ============================================================================
# Panel principal
# ============================================================================
def selector_mes(df, clave):
    actual = an.periodo_de(ahora())
    meses = sorted(set(df["fecha_hora"].dt.strftime("%Y-%m")) | {actual}, reverse=True) if not df.empty else [actual]
    return st.selectbox("Mes", meses, index=meses.index(actual), key=clave)


def pantalla_panel(df, presupuestos):
    st.title("Panel principal")
    periodo = selector_mes(df, "mes_panel")
    df_mes = an.filtrar_mes(df, periodo)
    resumen = an.resumen_mes(df_mes)
    ingreso_ref = an.ingreso_referencia(df_mes, bd.ingreso_mensual())

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos del mes", an.pesos(resumen["ingresos"]))
    c2.metric("Gastos del mes", an.pesos(resumen["gastos"]))
    c3.metric("Saldo", an.pesos(resumen["saldo"]))

    if df_mes.empty:
        st.info("Todavía no hay movimientos este mes. Ve a «Registrar movimiento» para empezar.")
        return

    # --- Idea 1: presupuesto por categoría -----------------------------------
    st.subheader("Presupuesto por categoría")
    estado = an.estado_presupuesto(df_mes, presupuestos)
    col_a, col_b = st.columns(2)
    for i, fila in estado.iterrows():
        destino = col_a if i % 2 == 0 else col_b
        pct = fila["porcentaje"]
        marca = " · superado" if pct > 1 else (" · cerca del límite" if pct >= 0.8 else "")
        destino.progress(min(pct, 1.0),
                         text=f"{fila['categoria']}: {an.pesos(fila['gastado'])} de "
                              f"{an.pesos(fila['limite'])} ({pct:.0%}){marca}")

    # --- Idea 2: gastos hormiga ----------------------------------------------
    st.subheader("Gastos hormiga")
    h = an.analisis_hormiga(df_mes, periodo, ahora().date(), ingreso_ref)
    if h["cantidad"] == 0:
        st.success("No tienes gastos hormiga este mes.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cantidad", h["cantidad"])
        c2.metric("Total", an.pesos(h["total"]))
        c3.metric("Proyección del mes", an.pesos(h["proyeccion_mes"]))
        c4.metric("Proyección en un año", an.pesos(h["proyeccion_anual"]))
        texto = f"En promedio gastas {an.pesos(h['promedio'])} cada vez"
        if h["pct_ingreso"] is not None:
            texto += f", y al ritmo actual se llevarán el {h['pct_ingreso']:.1%} de tu ingreso del mes"
        texto += f". Suelen ocurrir en la {h['franja']}."
        st.write(texto)
        if h["frecuentes"]:
            st.write("Los que más se repiten:")
            for desc, veces, total in h["frecuentes"]:
                st.write(f"- {desc}: {veces} {'vez' if veces == 1 else 'veces'}, {an.pesos(total)}")

    # --- Idea 3: regla 50/30/20 ----------------------------------------------
    st.subheader("Regla 50/30/20")
    regla = an.regla_50_30_20(df_mes, ingreso_ref)
    st.caption(f"Calculada sobre un ingreso de {an.pesos(ingreso_ref)}. Necesidades: alimentación, "
               "transporte, vivienda y salud. Deseos: ocio y gastos hormiga. Ahorro: lo que sobra.")
    columnas = st.columns(3)
    for col, (nombre, b) in zip(columnas, regla["bloques"].items()):
        col.metric(nombre, f"{b['pct']:.0%}", delta=f"ideal {b['ideal']:.0%}", delta_color="off")
        col.progress(max(0.0, min(b["pct"], 1.0)), text=an.pesos(b["monto"]))
        col.write("Dentro de lo recomendado" if b["bien"] else "Fuera de lo recomendado")
    st.info(regla["consejo"])

    # --- Idea 4: movimientos inusuales ---------------------------------------
    st.subheader("Movimientos inusuales")
    inusuales = df_mes[df_mes["atipico"]]
    if inusuales.empty:
        st.success("La IA no detectó movimientos inusuales este mes.")
    else:
        for _, m in inusuales.iterrows():
            st.warning(f"{m['fecha_hora']:%d/%m %H:%M} · {m['descripcion']} · {an.pesos(m['monto'])} "
                       f"({m['categoria_final']}). {m['motivo_atipico']}")

    st.subheader("Gastos por categoría")
    st.bar_chart(an.gasto_por_categoria(df_mes))


# ============================================================================
# Registrar movimiento
# ============================================================================
def mostrar_mensaje_guardado():
    datos = st.session_state.pop("mensaje_guardado", None)
    if not datos:
        return
    nivel, mensaje, extra = datos
    {"ok": st.success, "aviso": st.warning, "peligro": st.error}[nivel](mensaje)
    if extra:
        st.info(extra)


def pantalla_registrar(df, presupuestos):
    st.title("Registrar movimiento")
    mostrar_mensaje_guardado()

    pendiente = st.session_state.get("pendiente")
    if pendiente is None:
        formulario_registro()
    else:
        revisar_prediccion(pendiente, df, presupuestos)


def formulario_registro():
    # La fecha por defecto se fija una sola vez para que no cambie mientras escribes
    if "fecha_defecto" not in st.session_state:
        st.session_state.fecha_defecto = ahora().replace(second=0, microsecond=0)
    defecto = st.session_state.fecha_defecto

    with st.form("nuevo_movimiento"):
        c1, c2 = st.columns([2, 1])
        monto = c1.number_input("Monto ($ COP)", min_value=0, step=1_000, value=None, placeholder="Ej: 15000")
        tipo = c2.radio("Tipo", ["Gasto", "Ingreso"], horizontal=True)
        descripcion = st.text_input("Descripción", placeholder="Ej: almuerzo corrientazo, Uber a la casa, tinto")
        with st.expander("Cambiar fecha y hora (por defecto, ahora)"):
            f1, f2 = st.columns(2)
            fecha = f1.date_input("Fecha", value=defecto.date())
            hora = f2.time_input("Hora", value=defecto.time())
        enviado = st.form_submit_button("Clasificar con IA", type="primary")

    if enviado:
        if not monto or monto <= 0:
            st.error("Escribe un monto mayor que cero.")
            return
        if not descripcion.strip():
            st.error("Escribe una descripción para que la IA pueda clasificar el movimiento.")
            return
        fecha_hora = datetime.combine(fecha, hora)
        st.session_state.pendiente = {
            "fecha_hora": fecha_hora,
            "monto": float(monto),
            "tipo": tipo,
            "descripcion": descripcion.strip(),
            "resultado": motor.predecir(fecha_hora, monto, tipo, descripcion),
        }
        st.rerun()


def revisar_prediccion(p, df, presupuestos):
    r = p["resultado"]
    st.write(f"**{p['descripcion']}** · {an.pesos(p['monto'])} · {p['tipo']} · "
             f"{p['fecha_hora']:%d/%m/%Y %H:%M}")

    c1, c2 = st.columns([1, 2])
    c1.metric("Categoría sugerida", r["categoria"])
    c2.progress(r["confianza"], text=f"Confianza de la IA: {r['confianza']:.0%}")
    if len(r["ranking"]) > 1 and r["ranking"][1][1] > 0:
        c2.caption("Otras opciones: " + ", ".join(f"{c} ({v:.0%})" for c, v in r["ranking"][1:3] if v > 0))

    if r["categoria_modelo"] != r["categoria"]:
        st.info(f"El modelo pensó en «{r['categoria_modelo']}», pero como es un {p['tipo'].lower()} "
                f"se ajustó a «{r['categoria']}».")

    # Idea 4: aviso de movimiento inusual
    if r["atipico"]:
        st.warning("Movimiento inusual. " + r["motivo_atipico"])

    # Confirmar o corregir
    opciones = ["Ingresos"] if p["tipo"] == "Ingreso" else bd.CATEGORIAS_GASTO
    if r["segura"]:
        indice = opciones.index(r["categoria"])
    else:
        st.warning("No estoy segura de esta categoría. Por favor elige la correcta.")
        indice = None
    categoria = st.selectbox("Categoría final", opciones, index=indice, placeholder="Elige una categoría")

    # Idea 1: alerta de presupuesto en el momento
    nivel, alerta = "ok", None
    if categoria and p["tipo"] == "Gasto":
        df_mes = an.filtrar_mes(df, an.periodo_de(p["fecha_hora"]))
        nivel, alerta = an.alerta_registro(categoria, p["monto"], df_mes, presupuestos)
        {"ok": st.success, "aviso": st.warning, "peligro": st.error}[nivel](alerta)

    # Explicación: los 5 vecinos
    with st.expander("¿Por qué esta categoría? Los 5 movimientos más parecidos", expanded=True):
        vecinos = pd.DataFrame([{
            "Origen": v["origen"],
            "Descripción": v["descripcion"],
            "Monto": an.pesos(v["monto"]),
            "Tipo": v["tipo"],
            "Cuándo": v["cuando"],
            "Categoría": v["categoria"],
            "Distancia": round(v["distancia"], 2),
        } for v in r["vecinos"]])
        st.dataframe(vecinos, hide_index=True)
        if r["palabras_reconocidas"]:
            st.caption("Palabras que la IA reconoció: " + ", ".join(r["palabras_reconocidas"]))
        st.caption("Distancia menor = más parecido. La IA vota con estos 5 vecinos; "
                   "los más cercanos pesan más.")

    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("Guardar", type="primary", disabled=categoria is None):
        bd.guardar_movimiento(
            p["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S"), p["monto"], p["tipo"], p["descripcion"],
            r["categoria"], r["confianza"], categoria, r["atipico"], r["motivo_atipico"],
        )
        if p["tipo"] == "Ingreso":
            nivel, alerta = "ok", f"Ingreso de {an.pesos(p['monto'])} guardado."
        extra = ("Corregiste a la IA: desde ya usará este movimiento como ejemplo."
                 if categoria != r["categoria"] else "La IA agregó este movimiento a sus ejemplos.")
        st.session_state.mensaje_guardado = (nivel, "Guardado. " + (alerta or ""), extra)
        limpiar_registro()
        st.rerun()
    if b2.button("Cancelar"):
        limpiar_registro()
        st.rerun()


def limpiar_registro():
    st.session_state.pop("pendiente", None)
    st.session_state.pop("fecha_defecto", None)


# ============================================================================
# Historial
# ============================================================================
def pantalla_historial(df):
    st.title("Historial")
    if (msg := st.session_state.pop("mensaje_historial", None)):
        st.success(msg)

    precision, n = an.precision_real(df)
    if precision is not None:
        st.metric("Precisión real de la IA con tus datos", f"{precision:.0%}",
                  help="Porcentaje de movimientos en los que no tuviste que cambiar la categoría.")
        st.caption(f"Calculada sobre {n} movimientos. Es más honesta que la precisión del "
                   "entrenamiento, porque usa datos reales.")
    if df.empty:
        st.info("Aún no hay movimientos registrados.")
        return

    c1, c2 = st.columns(2)
    meses = ["Todos"] + sorted(set(df["fecha_hora"].dt.strftime("%Y-%m")), reverse=True)
    mes = c1.selectbox("Mes", meses)
    categorias = c2.multiselect("Categorías", bd.CATEGORIAS, placeholder="Todas")
    vista = df if mes == "Todos" else an.filtrar_mes(df, mes)
    if categorias:
        vista = vista[vista["categoria_final"].isin(categorias)]

    tabla = vista[["id", "fecha_hora", "descripcion", "monto", "tipo_movimiento",
                   "categoria_ia", "confianza", "categoria_final", "atipico"]].copy()
    tabla["eliminar"] = False

    editada = st.data_editor(
        tabla,
        hide_index=True,
        disabled=["id", "fecha_hora", "descripcion", "monto", "tipo_movimiento",
                  "categoria_ia", "confianza", "atipico"],
        column_config={
            "id": None,  # oculta la columna
            "fecha_hora": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
            "descripcion": "Descripción",
            "monto": st.column_config.NumberColumn("Monto", format="$ %d"),
            "tipo_movimiento": "Tipo",
            "categoria_ia": "Propuesta IA",
            "confianza": st.column_config.ProgressColumn("Confianza", min_value=0, max_value=1, format="%.2f"),
            "categoria_final": st.column_config.SelectboxColumn("Categoría final", options=bd.CATEGORIAS,
                                                                required=True),
            "atipico": st.column_config.CheckboxColumn("Inusual"),
            "eliminar": st.column_config.CheckboxColumn("Eliminar"),
        },
        key="editor_historial",
    )
    st.caption("Cambia la «Categoría final» para corregir a la IA, o marca «Eliminar». "
               "Luego presiona «Guardar cambios».")

    if st.button("Guardar cambios", type="primary"):
        original = tabla.set_index("id")
        corregidos, eliminados, rechazados = 0, 0, 0
        for _, fila in editada.iterrows():
            if fila["eliminar"]:
                bd.eliminar_movimiento(fila["id"])
                eliminados += 1
            elif fila["categoria_final"] != original.loc[fila["id"], "categoria_final"]:
                es_ingreso = fila["tipo_movimiento"] == "Ingreso"
                if es_ingreso != (fila["categoria_final"] == "Ingresos"):
                    rechazados += 1  # un gasto no puede ser "Ingresos" ni al revés
                    continue
                bd.corregir_categoria(fila["id"], fila["categoria_final"])
                corregidos += 1
        msg = f"{corregidos} corregidos y {eliminados} eliminados. La IA ya aprendió de los cambios."
        if rechazados:
            msg += f" {rechazados} cambios no se guardaron porque mezclaban gastos con ingresos."
        st.session_state.mensaje_historial = msg
        st.rerun()


# ============================================================================
# Presupuesto y ajustes
# ============================================================================
def pantalla_presupuesto(presupuestos):
    st.title("Presupuesto")
    if (msg := st.session_state.pop("mensaje_presupuesto", None)):
        st.success(msg)

    with st.form("presupuesto"):
        ingreso = st.number_input("Ingreso mensual aproximado ($ COP)", min_value=0, step=50_000,
                                  value=int(bd.ingreso_mensual()))
        columnas = st.columns(3)
        limites = {}
        for i, cat in enumerate(bd.CATEGORIAS_GASTO):
            limites[cat] = columnas[i % 3].number_input(cat, min_value=0, step=10_000,
                                                        value=int(presupuestos.get(cat, 0)))
        if st.form_submit_button("Guardar presupuesto", type="primary"):
            bd.guardar_config("ingreso_mensual", ingreso)
            bd.guardar_presupuestos(limites)
            st.session_state.mensaje_presupuesto = "Presupuesto actualizado."
            st.rerun()
    total = sum(presupuestos.values())
    ingreso_actual = bd.ingreso_mensual()
    st.caption(f"Total asignado: {an.pesos(total)} de {an.pesos(ingreso_actual)}"
               + (f" (queda {an.pesos(ingreso_actual - total)} para ahorro)." if ingreso_actual >= total else "."))

    with st.expander("Opciones del prototipo"):
        if st.button("Cargar movimientos de ejemplo"):
            cargar_demo(motor, ahora())
            st.session_state.mensaje_presupuesto = "Se cargaron los movimientos de ejemplo."
            st.rerun()
        st.write("Reiniciar borra todos los movimientos y presupuestos.")
        confirmar = st.checkbox("Sí, quiero borrar todo")
        if st.button("Reiniciar prototipo", disabled=not confirmar):
            bd.borrar_todo()
            st.session_state.clear()
            st.rerun()


# ============================================================================
# Navegación
# ============================================================================
if not bd.esta_configurado():
    pantalla_bienvenida()
else:
    presupuestos = bd.leer_presupuestos()
    st.sidebar.title("FinanzIA")
    pagina = st.sidebar.radio("Ir a", ["Panel", "Registrar movimiento", "Historial", "Presupuesto"])
    st.sidebar.divider()
    st.sidebar.caption(f"La IA conoce {motor.total_ejemplos} ejemplos: {motor.n_base} del "
                       f"entrenamiento y {motor.total_ejemplos - motor.n_base} tuyos.")

    if pagina == "Panel":
        pantalla_panel(movimientos, presupuestos)
    elif pagina == "Registrar movimiento":
        pantalla_registrar(movimientos, presupuestos)
    elif pagina == "Historial":
        pantalla_historial(movimientos)
    else:
        pantalla_presupuesto(presupuestos)
