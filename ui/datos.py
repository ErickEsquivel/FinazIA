"""
ui/datos.py
-----------
Acceso a datos compartido por todas las pantallas: el motor de IA (cargado una
sola vez) y los movimientos (leídos de SQLite solo cuando algo cambia).
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

import base_datos as bd
from modelo_ia import MotorIA, cargar_pipeline

RUTA_MODELO = Path(__file__).resolve().parent.parent / "ia_clasificadora_multivariable_knn.pkl"
ZONA = ZoneInfo("America/Bogota")


def ahora():
    """Fecha y hora de Colombia (el servidor de Streamlit Cloud está en otra zona)."""
    return datetime.now(ZONA).replace(tzinfo=None)


@st.cache_resource(show_spinner="Cargando la IA…")
def obtener_motor():
    return MotorIA(cargar_pipeline(RUTA_MODELO))


@st.cache_data(show_spinner=False, max_entries=5)
def _leer_movimientos(version):
    return bd.leer_movimientos()


def movimientos():
    """Movimientos actuales. La IA vuelve a aprender solo si los datos cambiaron."""
    version = bd.version_datos()
    df = _leer_movimientos(version)
    obtener_motor().aprender(df, version)
    return df
