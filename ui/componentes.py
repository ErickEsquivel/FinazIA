"""
ui/componentes.py
-----------------
Piezas de interfaz reutilizables: categorías con icono y color, montos,
barras de presupuesto, selector de mes, mensajes y el formulario de límites.
"""

import html
import re

import pandas as pd
import streamlit as st

import analisis as an
import base_datos as bd
from ui.tema import AMBAR, ROJO, VERDE

# Icono y color fijos por categoría (el color sigue a la categoría, nunca al orden)
CATEGORIA_UI = {
    "Alimentación": ("🍽️", "#2A78D6"),
    "Transporte": ("🚌", "#EB6834"),
    "Vivienda y Servicios": ("🏠", "#1BAF7A"),
    "Ocio y Entretenimiento": ("🎬", "#EDA100"),
    "Gastos Hormiga": ("🐜", "#E87BA4"),
    "Salud y Educación": ("🩺", "#6250D6"),
    "Ingresos": ("💰", "#008300"),
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

PAGINA_REGISTRAR = "vistas/registrar.py"


# ----------------------------------------------------------------------------
# Texto y formato
# ----------------------------------------------------------------------------
def esc(texto) -> str:
    return html.escape(str(texto))


def icono(categoria) -> str:
    return CATEGORIA_UI.get(categoria, ("•", "#888"))[0]


def color(categoria) -> str:
    return CATEGORIA_UI.get(categoria, ("•", "#888888"))[1]


def con_icono(categoria) -> str:
    """'Alimentación' -> '🍽️ Alimentación' (para pills y selectbox)."""
    return f"{icono(categoria)} {categoria}"


def nombre_mes(periodo: str) -> str:
    """'2026-11' -> 'Noviembre 2026'."""
    anio, mes = periodo.split("-")
    return f"{MESES[int(mes) - 1].capitalize()} {anio}"


def fecha_larga(fecha) -> str:
    """Timestamp -> 'lunes 10 de noviembre'."""
    f = pd.Timestamp(fecha)
    return f"{DIAS[f.dayofweek]} {f.day} de {MESES[f.month - 1]}"


def monto_html(valor, tipo="Gasto", clase="") -> str:
    signo = "−" if tipo == "Gasto" else "+"
    css = "fz-gasto" if tipo == "Gasto" else "fz-ingreso"
    return f'<span class="fz-monto {css} {clase}">{signo}{an.pesos(valor)}</span>'


def icono_redondo(categoria) -> str:
    c = color(categoria)
    return f'<span class="fz-ico" style="background:{c}22">{icono(categoria)}</span>'


# ----------------------------------------------------------------------------
# Campo de pesos: muestra 1.250.000 dentro del mismo campo mientras se escribe.
# El formateo en vivo lo hace el script de ui/tema.py sobre los campos cuya
# clave empieza por "pesos_"; aquí se convierte el texto de vuelta a número.
# ----------------------------------------------------------------------------
def formato_miles(valor) -> str:
    """1250000 -> '1.250.000'; None o vacío -> ''."""
    return "" if valor in (None, "") else f"{int(valor):,}".replace(",", ".")


def leer_pesos(texto):
    """'1.250.000' -> 1250000. Ignora lo que vaya después de una coma (centavos)."""
    digitos = re.sub(r"\D", "", str(texto or "").split(",")[0])
    return int(digitos) if digitos else None


def clave_pesos(clave) -> str:
    return f"pesos_{clave}"


def fijar_pesos(clave, valor):
    st.session_state[clave_pesos(clave)] = formato_miles(valor)


def campo_pesos(etiqueta, clave, valor=None, placeholder="Ej: 15.000", ayuda=None):
    """Campo de texto para montos en pesos. Devuelve un entero o None si está vacío."""
    k = clave_pesos(clave)
    # Normaliza antes de dibujar el campo (por si se pegó texto o el script no corrió)
    st.session_state[k] = formato_miles(leer_pesos(st.session_state[k] if k in st.session_state else valor))
    texto = st.text_input(etiqueta, key=k, placeholder=placeholder, help=ayuda,
                          icon=":material/attach_money:")
    return leer_pesos(texto)


def chip(categoria) -> str:
    c = color(categoria)
    return (f'<span class="fz-chip" style="border-color:{c}66;background:{c}1A">'
            f'{icono(categoria)} {esc(categoria)}</span>')


def titulo_tarjeta(texto, derecha=""):
    st.html(f'<div class="fz-titulo" style="display:flex;justify-content:space-between;gap:.5rem">'
            f'<span>{texto}</span><span class="fz-muted">{derecha}</span></div>')


def estado_vacio(emoji, titulo, texto):
    st.html(f'<div class="fz-vacio"><div class="em">{emoji}</div>'
            f'<div class="fz-titulo">{titulo}</div><div class="fz-muted">{texto}</div></div>')


# ----------------------------------------------------------------------------
# Barras de progreso con color según el estado
# ----------------------------------------------------------------------------
def color_estado(pct) -> str:
    return ROJO if pct > 1 else (AMBAR if pct >= 0.8 else VERDE)


def barra_html(nombre, pct, cab_derecha, pie_izq, pie_der="", color_barra=None) -> str:
    ancho = max(0.0, min(pct, 1.0)) * 100
    c = color_barra or color_estado(pct)
    return (f'<div class="fz-barra"><div class="cab"><span class="nom">{nombre}</span>'
            f'<span class="fz-monto">{cab_derecha}</span></div>'
            f'<div class="fz-pista"><div class="fz-relleno" style="width:{ancho:.1f}%;background:{c}"></div></div>'
            f'<div class="pie"><span>{pie_izq}</span><span>{pie_der}</span></div></div>')


def barra_presupuesto(fila) -> str:
    pct, restante = fila["porcentaje"], fila["restante"]
    if fila["limite"] <= 0:
        pie = "Sin límite definido"
    elif restante >= 0:
        pie = f"Te quedan {an.pesos(restante)}"
    else:
        pie = f'<b style="color:{ROJO}">Superado por {an.pesos(-restante)}</b>'
    return barra_html(con_icono(fila["categoria"]), pct,
                      f'{an.pesos(fila["gastado"])} <span class="fz-muted">/ {an.pesos(fila["limite"])}</span>',
                      pie, f"{pct:.0%}" if fila["limite"] > 0 else "")


# ----------------------------------------------------------------------------
# Selector de mes con flechas (Inicio) y lista de meses (Movimientos)
# ----------------------------------------------------------------------------
def meses_disponibles(df, actual) -> list:
    meses = set(df["fecha_hora"].dt.strftime("%Y-%m")) if not df.empty else set()
    return sorted(meses | {actual}, reverse=True)


def selector_mes_flechas(df, actual, clave="mes_inicio") -> str:
    meses = meses_disponibles(df, actual)  # del más reciente al más antiguo
    if st.session_state.get(clave) not in meses:
        st.session_state[clave] = actual
    i = meses.index(st.session_state[clave])

    def mover(paso):
        st.session_state[clave] = meses[i + paso]

    with st.container(horizontal=True, vertical_alignment="center", wrap=False, key="navmes"):
        st.button("", icon=":material/chevron_left:", key=f"{clave}_ant", disabled=i >= len(meses) - 1,
                  on_click=mover, args=(1,), help="Mes anterior")
        st.html(f'<div class="fz-mes">{nombre_mes(meses[i])}</div>', width="stretch")
        st.button("", icon=":material/chevron_right:", key=f"{clave}_sig", disabled=i == 0,
                  on_click=mover, args=(-1,), help="Mes siguiente")
    return meses[i]


# ----------------------------------------------------------------------------
# Mensajes: un solo patrón para avisos y para "flash" entre recargas
# ----------------------------------------------------------------------------
_AVISOS = {
    "ok": (st.success, ":material/check_circle:"),
    "aviso": (st.warning, ":material/warning:"),
    "peligro": (st.error, ":material/error:"),
    "info": (st.info, ":material/info:"),
}


def avisar(nivel, texto):
    funcion, ico = _AVISOS[nivel]
    funcion(texto, icon=ico)


def flash(texto, nivel="ok", detalle=None):
    """Guarda un mensaje para mostrarlo después del próximo st.rerun()."""
    st.session_state["_flash"] = (nivel, texto, detalle)


def mostrar_flash():
    datos = st.session_state.pop("_flash", None)
    if not datos:
        return
    nivel, texto, detalle = datos
    if nivel == "ok":
        st.toast(texto, icon=":material/check_circle:")
    else:
        avisar(nivel, texto)
    if detalle:
        st.toast(detalle, icon=":material/psychology:")


def ir_a_registrar(tipo="Gasto"):
    st.session_state["borrador"] = {"tipo": tipo}
    st.session_state.pop("pendiente", None)
    st.switch_page(PAGINA_REGISTRAR)


# ----------------------------------------------------------------------------
# Formulario de límites por categoría (Bienvenida y Presupuesto)
# Va FUERA de st.form para que el total se actualice mientras escribes.
# ----------------------------------------------------------------------------
def sugeridos(ingreso) -> dict:
    return {c: int(round(ingreso * bd.PORCENTAJE_SUGERIDO[c], -3)) for c in bd.CATEGORIAS_GASTO}


def aplicar_sugeridos(prefijo, ingreso, valores=None):
    for cat, valor in (valores or sugeridos(ingreso)).items():
        fijar_pesos(f"{prefijo}_{cat}", valor)


def formulario_limites(prefijo, ingreso, iniciales: dict) -> dict:
    columnas = st.columns(2)
    limites = {}
    for i, cat in enumerate(bd.CATEGORIAS_GASTO):
        with columnas[i % 2]:
            limites[cat] = campo_pesos(
                con_icono(cat), f"{prefijo}_{cat}", int(iniciales.get(cat, 0)), placeholder="0",
                ayuda=f"Sugerido: {bd.PORCENTAJE_SUGERIDO[cat]:.0%} del ingreso",
            ) or 0

    total = sum(limites.values())
    libre = ingreso - total
    pct = total / ingreso if ingreso > 0 else 0
    pie = (f"Quedan {an.pesos(libre)} para ahorro ({libre / ingreso:.0%})" if ingreso > 0 and libre >= 0
           else f'<b style="color:{ROJO}">Te pasas {an.pesos(-libre)} de tu ingreso</b>' if ingreso > 0
           else "Define tu ingreso para comparar")
    st.html(barra_html("Total asignado", pct,
                       f'{an.pesos(total)} <span class="fz-muted">/ {an.pesos(ingreso)}</span>', pie,
                       color_barra=ROJO if pct > 1 else VERDE))
    st.button("Usar límites sugeridos", icon=":material/auto_fix_high:", key=f"{prefijo}_sug",
              on_click=aplicar_sugeridos, args=(prefijo, ingreso), type="tertiary")
    return limites
