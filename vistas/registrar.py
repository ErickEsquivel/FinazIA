"""
Registrar: registro rápido en dos toques.
  1) Tipo, monto y descripción.
  2) La IA propone la categoría; confirmas o la cambias con un toque y guardas.
"""

from datetime import datetime

import streamlit as st

import analisis as an
import base_datos as bd
from ui import componentes as ui
from ui import datos

motor = datos.obtener_motor()
df = datos.movimientos()
presupuestos = bd.leer_presupuestos()


def limpiar():
    st.session_state.pop("pendiente", None)
    st.session_state.pop("borrador", None)


def volver_a_editar():
    p = st.session_state.pop("pendiente")
    st.session_state.borrador = {k: p[k] for k in ("tipo", "monto", "descripcion", "fecha_hora")}


# ----------------------------------------------------------------------------
# Paso 1: formulario
# ----------------------------------------------------------------------------
def formulario():
    b = st.session_state.get("borrador", {})
    defecto = b.get("fecha_hora") or datos.ahora().replace(second=0, microsecond=0)
    errores = st.session_state.pop("errores_registro", {})

    # Sin st.form: así el valor en pesos se actualiza apenas escribes el monto
    with st.container(border=True, key="card_registro"):
        tipo = st.segmented_control("Tipo", ["Gasto", "Ingreso"], default=b.get("tipo", "Gasto"),
                                    required=True, width="stretch", label_visibility="collapsed",
                                    format_func=lambda t: f"− {t}" if t == "Gasto" else f"+ {t}")
        monto = st.number_input("Monto ($ COP)", min_value=0, step=1_000, value=b.get("monto"),
                                placeholder="Ej: 15000", icon=":material/attach_money:")
        if "monto" in errores:
            st.caption(f":red[{errores['monto']}]")
        elif monto:
            ui.valor_exacto(monto, tipo or "Gasto")
        descripcion = st.text_input("Descripción", value=b.get("descripcion", ""),
                                    placeholder="Ej: almuerzo corrientazo, Uber a la casa, tinto",
                                    icon=":material/edit_note:")
        if "descripcion" in errores:
            st.caption(f":red[{errores['descripcion']}]")
        es_ahora = abs((defecto - datos.ahora()).total_seconds()) < 3600
        with st.expander(f"📅 {'Hoy, ' if es_ahora else ''}{defecto:%d/%m/%Y %H:%M} · cambiar"):
            f1, f2 = st.columns(2)
            fecha = f1.date_input("Fecha", value=defecto.date(), format="DD/MM/YYYY")
            hora = f2.time_input("Hora", value=defecto.time())
        enviado = st.button("Continuar", type="primary", icon=":material/auto_awesome:",
                            width="stretch")

    if enviado:
        errores = {}
        if not monto or monto <= 0:
            errores["monto"] = "Escribe un monto mayor que cero."
        if not descripcion.strip():
            errores["descripcion"] = "Describe el movimiento para que la IA pueda clasificarlo."
        if errores:
            st.session_state.errores_registro = errores
            st.session_state.borrador = {"tipo": tipo, "monto": monto, "descripcion": descripcion,
                                         "fecha_hora": datetime.combine(fecha, hora)}
            st.rerun()
        fecha_hora = datetime.combine(fecha, hora)
        st.session_state.pendiente = {
            "fecha_hora": fecha_hora,
            "monto": float(monto),
            "tipo": tipo,
            "descripcion": descripcion.strip(),
            "resultado": motor.predecir(fecha_hora, monto, tipo, descripcion),
        }
        st.rerun()

    st.caption(f"🧠 La IA conoce {motor.total_ejemplos} ejemplos: {motor.n_base} del entrenamiento "
               f"y {motor.total_ejemplos - motor.n_base} tuyos.")


# ----------------------------------------------------------------------------
# Paso 2: revisar la categoría y guardar
# ----------------------------------------------------------------------------
def revisar(p):
    r = p["resultado"]
    with st.container(border=True, key="card_revision"):
        st.html(f'<div class="fz-muted">{p["fecha_hora"]:%d/%m/%Y %H:%M} · {p["tipo"]}</div>'
                f'<div class="fz-grande">{ui.monto_html(p["monto"], p["tipo"])}</div>'
                f'<div style="font-size:1.05rem;margin-bottom:.6rem">{ui.esc(p["descripcion"])}</div>')

        opciones = ["Ingresos"] if p["tipo"] == "Ingreso" else bd.CATEGORIAS_GASTO
        if r["segura"]:
            st.html(f'<div>✨ La IA sugiere <b>{ui.esc(r["categoria"])}</b> '
                    f'<span class="fz-muted">· {r["confianza"]:.0%} de confianza</span></div>')
            etiqueta = "¿Es correcta? Si no, toca la correcta"
        else:
            ui.avisar("aviso", "No estoy segura de la categoría. Elige la correcta con un toque.")
            etiqueta = "Categoría"

        # Ordena las opciones según la IA: la más probable primero
        orden = [c for c, _ in r["ranking"] if c in opciones]
        categoria = st.pills(etiqueta, orden, default=r["categoria"] if r["segura"] else None,
                             format_func=ui.con_icono, key="pills_categoria")

        if r["categoria_modelo"] != r["categoria"]:
            st.caption(f"El modelo pensó en «{r['categoria_modelo']}», pero como es un "
                       f"{p['tipo'].lower()} se ajustó a «{r['categoria']}».")
        if r["atipico"]:
            ui.avisar("aviso", "Movimiento inusual. " + r["motivo_atipico"])

        # Alerta de presupuesto en el momento de registrar
        nivel, alerta = "ok", None
        if categoria and p["tipo"] == "Gasto":
            df_mes = an.filtrar_mes(df, an.periodo_de(p["fecha_hora"]))
            nivel, alerta = an.alerta_registro(categoria, p["monto"], df_mes, presupuestos)
            ui.avisar(nivel if nivel != "ok" else "info", alerta)

        with st.container(horizontal=True):
            guardar = st.button("Guardar", type="primary", icon=":material/check:",
                                disabled=categoria is None, width="stretch")
            st.button("Editar", icon=":material/edit:", on_click=volver_a_editar, width="stretch")
            st.button("Cancelar", icon=":material/close:", on_click=limpiar, type="tertiary")

    with st.expander("🔍 ¿Por qué esta categoría?"):
        st.caption("La IA busca los 5 movimientos más parecidos (por palabras, monto y hora) "
                   "y vota con ellos; los más parecidos pesan más.")
        if r["palabras_reconocidas"]:
            st.markdown("Palabras que reconoció: " + " ".join(f"`{w}`" for w in r["palabras_reconocidas"]))
        filas = []
        for v in r["vecinos"]:
            desc = v["descripcion"].replace("palabras: ", "") if v["origen"] == "Entrenamiento" else v["descripcion"]
            filas.append(f'<div class="fz-mov" style="margin:.45rem 0">{ui.icono_redondo(v["categoria"])}'
                         f'<div class="txt"><div class="desc">{ui.esc(desc)}</div>'
                         f'<div class="meta">{v["origen"]} · {v["cuando"]} · {ui.esc(v["categoria"])}</div></div>'
                         f'<span style="margin-left:auto">{ui.monto_html(v["monto"], v["tipo"])}</span></div>')
        st.html("".join(filas))

    if guardar:
        bd.guardar_movimiento(
            p["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S"), p["monto"], p["tipo"], p["descripcion"],
            r["categoria"], r["confianza"], categoria, r["atipico"], r["motivo_atipico"],
        )
        detalle = ("Corregiste a la IA: desde ya usará este movimiento como ejemplo."
                   if categoria != r["categoria"] else None)
        if p["tipo"] == "Ingreso":
            ui.flash(f"Ingreso de {an.pesos(p['monto'])} guardado.", "ok", detalle)
        else:
            ui.flash(f"Gasto guardado en {categoria}. {alerta or ''}", nivel, detalle)
        limpiar()
        st.rerun()


# ----------------------------------------------------------------------------
with st.container(key="centrado_registro"):
    st.title("Nuevo movimiento")
    ui.mostrar_flash()
    pendiente = st.session_state.get("pendiente")
    if pendiente is None:
        formulario()
    else:
        revisar(pendiente)
