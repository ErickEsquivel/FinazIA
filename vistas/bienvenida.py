"""Bienvenida: asistente de 3 pasos (ingreso → límites → datos de ejemplo)."""

import streamlit as st

import analisis as an
import base_datos as bd
from datos_demo import cargar_demo
from ui import componentes as ui
from ui import datos

PASOS = ["Tu ingreso", "Tus límites", "Listo"]
paso = st.session_state.setdefault("paso_bienvenida", 0)


def ir(n):
    st.session_state.paso_bienvenida = n


with st.container(key="centrado_bienvenida"):
    st.title("Bienvenido a FinanzIA 👋")
    st.html('<div class="fz-pasos">' + "".join(
        f'<div class="{"on" if i <= paso else ""}"></div>' for i in range(len(PASOS))) + "</div>"
        + f'<div class="fz-muted">Paso {paso + 1} de {len(PASOS)} · {PASOS[paso]}</div>')

    with st.container(border=True, key="card_paso"):
        if paso == 0:
            st.subheader("¿Cuánto recibes al mes?")
            st.caption("Con esto te proponemos un límite para cada categoría. "
                       "Puedes cambiarlo cuando quieras.")
            # El valor se guarda aparte porque Streamlit borra el estado de los
            # widgets que dejan de mostrarse (al pasar al siguiente paso).
            ingreso = st.number_input("Ingreso mensual aproximado ($ COP)", min_value=0, step=50_000,
                                      value=st.session_state.get("bv_ingreso", 1_500_000))
            st.session_state.bv_ingreso = ingreso
            ui.valor_exacto(ingreso, "Ingreso")
            if ingreso <= 0:
                st.caption(":orange[Escribe un valor mayor que cero para sugerirte límites.]")
            if st.button("Continuar", type="primary", icon=":material/arrow_forward:",
                         disabled=ingreso <= 0, width="stretch"):
                if st.session_state.get("bv_limites_de") != ingreso:  # ingreso nuevo → nuevos sugeridos
                    st.session_state.bv_limites = ui.sugeridos(ingreso)
                    st.session_state.bv_limites_de = ingreso
                ui.aplicar_sugeridos("bv", ingreso, st.session_state.bv_limites)
                ir(1)
                st.rerun()

        elif paso == 1:
            ingreso = st.session_state.bv_ingreso
            st.subheader("Tu límite mensual por categoría")
            st.caption(f"Te sugerimos estos valores según tu ingreso de {an.pesos(ingreso)}. "
                       "Lo que no asignes queda como ahorro.")
            limites = ui.formulario_limites("bv", ingreso, st.session_state.bv_limites)
            st.session_state.bv_limites = limites
            with st.container(horizontal=True):
                if st.button("Atrás", icon=":material/arrow_back:", width="stretch"):
                    ir(0)
                    st.rerun()
                if st.button("Continuar", type="primary", icon=":material/arrow_forward:",
                             width="stretch"):
                    ir(2)
                    st.rerun()

        else:
            st.subheader("¿Quieres probar con datos de ejemplo?")
            st.caption("Cargamos un mes típico para que veas el panel, los gráficos y las alertas "
                       "funcionando. Puedes borrarlos después desde Presupuesto → Ajustes.")
            demo = st.toggle("Cargar movimientos de ejemplo", value=True)
            atras = empezar = False
            with st.container(horizontal=True):
                atras = st.button("Atrás", icon=":material/arrow_back:", width="stretch")
                empezar = st.button("Empezar", type="primary", icon=":material/rocket_launch:",
                                    width="stretch")
            if atras:
                ir(1)
                st.rerun()
            if empezar:
                bd.guardar_config("ingreso_mensual", st.session_state.bv_ingreso)
                bd.guardar_presupuestos(st.session_state.bv_limites)
                bd.guardar_config("configurado", "si")
                if demo:
                    cargar_demo(datos.obtener_motor(), datos.ahora())
                for clave in [k for k in st.session_state if k.startswith("bv") or k == "paso_bienvenida"]:
                    del st.session_state[clave]
                ui.flash("¡Todo listo! Este es tu panel.")
                st.rerun()
