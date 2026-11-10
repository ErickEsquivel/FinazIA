"""Movimientos: buscar, filtrar, editar (la IA aprende de las correcciones) y borrar."""

from datetime import datetime

import streamlit as st

import analisis as an
import base_datos as bd
from ui import componentes as ui
from ui import datos

POR_PAGINA = 30

motor = datos.obtener_motor()
df = datos.movimientos()
ui.mostrar_flash()


# ----------------------------------------------------------------------------
# Diálogo para editar o eliminar un movimiento
# ----------------------------------------------------------------------------
@st.dialog("Editar movimiento", width="small")
def editar(mov):
    es_ingreso = mov["tipo_movimiento"] == "Ingreso"
    st.html(f'<div class="fz-muted">{mov["tipo_movimiento"]} · la IA propuso '
            f'{ui.esc(ui.con_icono(mov["categoria_ia"]))} ({mov["confianza"]:.0%})</div>')
    descripcion = st.text_input("Descripción", value=mov["descripcion"])
    monto = st.number_input("Monto ($ COP)", min_value=0, step=1_000, value=int(mov["monto"]))
    c1, c2 = st.columns(2)
    fecha = c1.date_input("Fecha", value=mov["fecha_hora"].date(), format="DD/MM/YYYY")
    hora = c2.time_input("Hora", value=mov["fecha_hora"].time())
    opciones = ["Ingresos"] if es_ingreso else bd.CATEGORIAS_GASTO
    categoria = st.pills("Categoría", opciones, default=mov["categoria_final"], required=True,
                         format_func=ui.con_icono)

    valido = monto > 0 and descripcion.strip()
    if not valido:
        st.caption(":red[El monto debe ser mayor que cero y la descripción no puede quedar vacía.]")

    confirmar = st.session_state.get("confirmar_borrado") == mov["id"]
    with st.container(horizontal=True):
        if st.button("Guardar", type="primary", icon=":material/check:", disabled=not valido,
                     width="stretch"):
            fecha_hora = datetime.combine(fecha, hora)
            atipico, motivo = mov["atipico"], mov["motivo_atipico"]
            if monto != mov["monto"] or descripcion.strip() != mov["descripcion"]:
                r = motor.predecir(fecha_hora, monto, mov["tipo_movimiento"], descripcion)
                atipico, motivo = r["atipico"], r["motivo_atipico"]
            bd.actualizar_movimiento(mov["id"], fecha_hora.strftime("%Y-%m-%d %H:%M:%S"), monto,
                                     descripcion, categoria, atipico, motivo)
            ui.flash("Movimiento actualizado.", "ok",
                     "La IA aprendió de tu corrección." if categoria != mov["categoria_final"] else None)
            st.rerun()
        if not confirmar:
            if st.button("Eliminar", icon=":material/delete:", width="stretch"):
                st.session_state.confirmar_borrado = mov["id"]
                st.rerun(scope="fragment")
    if confirmar:
        ui.avisar("peligro", "¿Seguro? Esta acción no se puede deshacer.")
        with st.container(horizontal=True):
            if st.button("Sí, eliminar", type="primary", icon=":material/delete_forever:", width="stretch"):
                bd.eliminar_movimiento(mov["id"])
                st.session_state.pop("confirmar_borrado", None)
                ui.flash("Movimiento eliminado.")
                st.rerun()
            if st.button("No", width="stretch"):
                st.session_state.pop("confirmar_borrado", None)
                st.rerun(scope="fragment")


# ----------------------------------------------------------------------------
# Encabezado
# ----------------------------------------------------------------------------
cab_izq, cab_der = st.columns([3, 1], vertical_alignment="bottom")
cab_izq.title("Movimientos")
if cab_der.button("Nuevo", icon=":material/add:", type="primary", width="stretch"):
    ui.ir_a_registrar()

if df.empty:
    with st.container(border=True, key="card_vacio"):
        ui.estado_vacio("🧾", "Aún no hay movimientos", "Cuando registres uno aparecerá aquí.")
    st.stop()

# ----------------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------------
with st.container(border=True, key="card_filtros"):
    buscar = st.text_input("Buscar", placeholder="Buscar por descripción…", icon=":material/search:",
                           label_visibility="collapsed")
    meses = ["Todos"] + ui.meses_disponibles(df, an.periodo_de(datos.ahora()))
    with st.container(horizontal=True, wrap=False):
        mes = st.selectbox("Mes", meses, index=1, width="stretch",
                           format_func=lambda m: "Todos los meses" if m == "Todos" else ui.nombre_mes(m))
        tipo = st.selectbox("Tipo", ["Todos", "Gastos", "Ingresos"], width="stretch")
    categorias = st.multiselect("Categorías", bd.CATEGORIAS, placeholder="Todas",
                                format_func=ui.con_icono)

vista = df if mes == "Todos" else an.filtrar_mes(df, mes)
if tipo != "Todos":
    vista = vista[vista["tipo_movimiento"] == tipo[:-1]]
if categorias:
    vista = vista[vista["categoria_final"].isin(categorias)]
if buscar.strip():
    vista = vista[vista["descripcion"].str.contains(buscar.strip(), case=False, regex=False)]

res = an.resumen_mes(vista)
precision, n = an.precision_real(df)
izq, der = st.columns([3, 2], vertical_alignment="center")
izq.html(f'<div class="fz-muted">{len(vista)} movimiento{"s" if len(vista) != 1 else ""} · '
         f'gastos <span class="fz-gasto fz-monto">{an.pesos(res["gastos"])}</span> · '
         f'ingresos <span class="fz-ingreso fz-monto">{an.pesos(res["ingresos"])}</span></div>')
if precision is not None:
    der.html(f'<div class="fz-muted" style="text-align:right" title="Movimientos en los que no tuviste '
             f'que cambiar la categoría ({n} en total)">🧠 La IA acierta el <b>{precision:.0%}</b> contigo</div>')

modo = st.segmented_control("Vista", ["Lista", "Tabla"], default="Lista", required=True,
                            label_visibility="collapsed",
                            format_func=lambda m: ("☰ " if m == "Lista" else "▦ ") + m)

if vista.empty:
    ui.estado_vacio("🔍", "Sin resultados", "Prueba con otros filtros.")
    st.stop()

# ----------------------------------------------------------------------------
# Vista lista: agrupada por día, cómoda en el celular
# ----------------------------------------------------------------------------
if modo == "Lista":
    limite = st.session_state.get("mostrar_n", POR_PAGINA)
    mostrar = vista.head(limite)
    with st.container(border=True, key="card_lista"):
        for dia, grupo in mostrar.groupby(mostrar["fecha_hora"].dt.date, sort=False):
            neto = an.resumen_mes(vista[vista["fecha_hora"].dt.date == dia])["saldo"]
            st.html(f'<div class="fz-dia"><span>{ui.fecha_larga(dia).capitalize()}</span>'
                    f'<span class="fz-monto">{an.pesos(neto)}</span></div>')
            for _, m in grupo.iterrows():
                with st.container(horizontal=True, vertical_alignment="center", wrap=False,
                                  key=f"fila_{m['id']}", gap="small"):
                    marca = " · ⚠️ inusual" if m["atipico"] else ""
                    corregido = " · ✏️ corregido" if m["categoria_ia"] != m["categoria_final"] else ""
                    st.html(f'<div class="fz-mov">{ui.icono_redondo(m["categoria_final"])}'
                            f'<div class="txt"><div class="desc">{ui.esc(m["descripcion"])}</div>'
                            f'<div class="meta">{ui.esc(m["categoria_final"])} · {m["fecha_hora"]:%H:%M}'
                            f'{marca}{corregido}</div></div></div>', width="stretch")
                    st.html(ui.monto_html(m["monto"], m["tipo_movimiento"]), width="content")
                    if st.button("", icon=":material/edit:", key=f"ed_{m['id']}", type="tertiary",
                                 help="Editar o eliminar"):
                        st.session_state.pop("confirmar_borrado", None)
                        editar(m)
    if len(vista) > limite:
        if st.button(f"Mostrar más ({len(vista) - limite} restantes)", icon=":material/expand_more:",
                     width="stretch"):
            st.session_state.mostrar_n = limite + POR_PAGINA
            st.rerun()

# ----------------------------------------------------------------------------
# Vista tabla: edición masiva
# ----------------------------------------------------------------------------
else:
    tabla = vista[["id", "fecha_hora", "descripcion", "monto", "tipo_movimiento",
                   "categoria_ia", "confianza", "categoria_final", "atipico"]].copy()
    tabla["eliminar"] = False
    editada = st.data_editor(
        tabla, hide_index=True, width="stretch",
        disabled=["id", "fecha_hora", "descripcion", "monto", "tipo_movimiento",
                  "categoria_ia", "confianza", "atipico"],
        column_config={
            "id": None,
            "fecha_hora": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
            "descripcion": "Descripción",
            "monto": st.column_config.NumberColumn("Monto", format="$ %d"),
            "tipo_movimiento": "Tipo",
            "categoria_ia": "Propuesta IA",
            "confianza": st.column_config.ProgressColumn("Confianza", min_value=0, max_value=1,
                                                         format="percent"),
            "categoria_final": st.column_config.SelectboxColumn("Categoría final", options=bd.CATEGORIAS,
                                                                required=True),
            "atipico": st.column_config.CheckboxColumn("Inusual"),
            "eliminar": st.column_config.CheckboxColumn("Eliminar"),
        },
        key="editor_movimientos",
    )

    original = tabla.set_index("id")["categoria_final"]
    cambiados = editada[(editada["categoria_final"] != editada["id"].map(original)) & ~editada["eliminar"]]
    mezclados = cambiados[(cambiados["tipo_movimiento"] == "Ingreso") != (cambiados["categoria_final"] == "Ingresos")]
    validos = cambiados.drop(mezclados.index)
    a_borrar = editada[editada["eliminar"]]

    if not mezclados.empty:
        ui.avisar("aviso", f"{len(mezclados)} cambio(s) no se guardarán: un gasto no puede ir a "
                           "«Ingresos» ni un ingreso a una categoría de gasto.")
    confirmado = True
    if not a_borrar.empty:
        confirmado = st.checkbox(f"Confirmo que quiero eliminar {len(a_borrar)} movimiento(s). "
                                 "No se puede deshacer.")
    hay_cambios = not validos.empty or not a_borrar.empty
    if st.button("Guardar cambios", type="primary", icon=":material/save:",
                 disabled=not hay_cambios or not confirmado):
        for _, fila in a_borrar.iterrows():
            bd.eliminar_movimiento(fila["id"])
        for _, fila in validos.iterrows():
            bd.corregir_categoria(fila["id"], fila["categoria_final"])
        partes = []
        if len(validos):
            partes.append(f"{len(validos)} corregido(s)")
        if len(a_borrar):
            partes.append(f"{len(a_borrar)} eliminado(s)")
        ui.flash(" y ".join(partes).capitalize() + ".", "ok",
                 "La IA aprendió de tus correcciones." if len(validos) else None)
        st.session_state.pop("editor_movimientos", None)
        st.rerun()
    if not hay_cambios:
        st.caption("Cambia la «Categoría final» para corregir a la IA o marca «Eliminar».")
