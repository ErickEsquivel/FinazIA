"""
app.py
------
Punto de entrada de FinanzIA (Streamlit).

Para ejecutarla en tu computador:
    streamlit run app.py

Este archivo solo arranca la app: tema, datos y navegación.
Cada pantalla vive en la carpeta vistas/:
  - bienvenida.py   (solo la primera vez) asistente de 3 pasos.
  - inicio.py       saldo del mes, categorías, presupuestos y análisis.
  - registrar.py    registro rápido: la IA clasifica, explica y alerta.
  - movimientos.py  buscar, filtrar, corregir (la IA aprende) y borrar.
  - presupuesto.py  límites por categoría y ajustes del prototipo.
"""

from pathlib import Path

import streamlit as st

import base_datos as bd
from ui import datos
from ui.tema import aplicar_estilos

st.set_page_config(page_title="FinanzIA", page_icon="💰", layout="wide",
                   initial_sidebar_state="collapsed")

bd.crear_tablas()
aplicar_estilos()
datos.movimientos()  # carga la IA y la pone al día con los movimientos guardados
st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

if not bd.esta_configurado():
    paginas = [st.Page("vistas/bienvenida.py", title="Bienvenida", icon=":material/waving_hand:")]
else:
    paginas = [
        st.Page("vistas/inicio.py", title="Inicio", icon=":material/home:", default=True),
        st.Page("vistas/registrar.py", title="Registrar", icon=":material/add_circle:"),
        st.Page("vistas/movimientos.py", title="Movimientos", icon=":material/receipt_long:"),
        st.Page("vistas/presupuesto.py", title="Presupuesto", icon=":material/savings:"),
    ]

st.navigation(paginas, position="top").run()
