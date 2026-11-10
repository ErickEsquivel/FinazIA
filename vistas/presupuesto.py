"""Presupuesto: ingreso y límites por categoría (con total en vivo) y ajustes del prototipo."""

import streamlit as st

import base_datos as bd
from datos_demo import cargar_demo
from ui import componentes as ui
from ui import datos

motor = datos.obtener_motor()
df = datos.movimientos()
presupuestos = bd.leer_presupuestos()

st.title("Presupuesto")
ui.mostrar_flash()

izq, der = st.columns([3, 2], gap="medium")

# ----------------------------------------------------------------------------
# Ingreso y límites
# ----------------------------------------------------------------------------
with izq, st.container(border=True, key="card_limites"):
    ui.titulo_tarjeta("Límite mensual por categoría")
    st.session_state.setdefault("pr_ingreso", int(bd.ingreso_mensual()))
    ingreso = st.number_input("Ingreso mensual aproximado ($ COP)", min_value=0, step=50_000,
                              key="pr_ingreso", icon=":material/payments:")
    limites = ui.formulario_limites("pr", ingreso, presupuestos)

    hay_cambios = (ingreso != int(bd.ingreso_mensual())
                   or any(int(v) != int(presupuestos.get(c, 0)) for c, v in limites.items()))
    if st.button("Guardar presupuesto", type="primary", icon=":material/save:",
                 disabled=not hay_cambios, width="stretch"):
        bd.guardar_config("ingreso_mensual", ingreso)
        bd.guardar_presupuestos(limites)
        ui.flash("Presupuesto actualizado.")
        st.rerun()
    if not hay_cambios:
        st.caption("No hay cambios sin guardar.")


# ----------------------------------------------------------------------------
# Ajustes
# ----------------------------------------------------------------------------
@st.dialog("¿Reiniciar FinanzIA?")
def confirmar_reinicio():
    st.write("Se borrarán **todos** los movimientos, presupuestos y la configuración. "
             "La IA olvidará lo que aprendió de ti. Esta acción no se puede deshacer.")
    with st.container(horizontal=True):
        if st.button("Sí, borrar todo", type="primary", icon=":material/delete_forever:", width="stretch"):
            bd.borrar_todo()
            st.session_state.clear()
            ui.flash("Se reinició la app. Empecemos de nuevo.")
            st.rerun()
        if st.button("Cancelar", width="stretch"):
            st.rerun()


@st.dialog("¿Cargar los ejemplos otra vez?")
def confirmar_demo():
    st.write(f"Ya tienes {len(df)} movimientos. Los ejemplos se **sumarán** a los actuales "
             "y podrían quedar duplicados.")
    with st.container(horizontal=True):
        if st.button("Cargar de todos modos", type="primary", width="stretch"):
            cargar_demo(motor, datos.ahora())
            ui.flash("Se cargaron los movimientos de ejemplo.")
            st.rerun()
        if st.button("Cancelar", width="stretch"):
            st.rerun()


with der:
    with st.container(border=True, key="card_ia"):
        ui.titulo_tarjeta("🧠 Tu IA")
        st.markdown(f"Conoce **{motor.total_ejemplos}** ejemplos: {motor.n_base} del entrenamiento "
                    f"y **{motor.total_ejemplos - motor.n_base}** tuyos. Cada vez que corriges una "
                    "categoría, aprende de ti.")

    with st.container(border=True, key="card_ajustes"):
        ui.titulo_tarjeta("Ajustes")
        st.caption("🌓 **Tema claro u oscuro:** menú ⋮ (arriba a la derecha) → *Settings* → *Theme*.")
        if st.button("Cargar movimientos de ejemplo", icon=":material/dataset:", width="stretch"):
            if df.empty:
                cargar_demo(motor, datos.ahora())
                ui.flash("Se cargaron los movimientos de ejemplo.")
                st.rerun()
            else:
                confirmar_demo()
        if st.button("Reiniciar la app", icon=":material/restart_alt:", width="stretch"):
            confirmar_reinicio()
