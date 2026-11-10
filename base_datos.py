"""
base_datos.py
-------------
Todo lo que tiene que ver con SQLite: crear las tablas, guardar movimientos,
leerlos, corregirlos y manejar los presupuestos.

SQLite guarda todo en un solo archivo (finanzia.db) junto a este código.
No necesita instalar ningún servidor: viene incluido con Python.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ZONA = ZoneInfo("America/Bogota")

# Ruta del archivo de la base de datos (queda en la misma carpeta del proyecto)
RUTA_BD = Path(__file__).parent / "finanzia.db"

# Las 7 categorías que conoce el modelo (deben escribirse EXACTAMENTE así)
CATEGORIAS = [
    "Alimentación",
    "Transporte",
    "Vivienda y Servicios",
    "Ocio y Entretenimiento",
    "Gastos Hormiga",
    "Salud y Educación",
    "Ingresos",
]
CATEGORIAS_GASTO = [c for c in CATEGORIAS if c != "Ingresos"]

# Porcentaje del ingreso que se sugiere como límite para cada categoría
# la primera vez que el usuario entra (lo puede cambiar después).
PORCENTAJE_SUGERIDO = {
    "Alimentación": 0.25,
    "Transporte": 0.10,
    "Vivienda y Servicios": 0.30,
    "Ocio y Entretenimiento": 0.10,
    "Gastos Hormiga": 0.05,
    "Salud y Educación": 0.05,
}


def conectar():
    """Abre una conexión a la base de datos."""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():
    """Crea las tablas si todavía no existen. Se llama cada vez que abre la app."""
    with conectar() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS movimientos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora       TEXT    NOT NULL,   -- 'AAAA-MM-DD HH:MM:SS'
                monto            REAL    NOT NULL,
                tipo_movimiento  TEXT    NOT NULL,   -- 'Gasto' o 'Ingreso'
                descripcion      TEXT    NOT NULL,
                categoria_ia     TEXT    NOT NULL,   -- lo que propuso la IA
                confianza        REAL    NOT NULL,   -- 0 a 1
                categoria_final  TEXT    NOT NULL,   -- lo que confirmó el usuario
                atipico          INTEGER NOT NULL DEFAULT 0,
                motivo_atipico   TEXT,
                actualizado_en   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS presupuestos (
                categoria       TEXT PRIMARY KEY,
                limite_mensual  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS configuracion (
                clave  TEXT PRIMARY KEY,
                valor  TEXT
            );
            """
        )


# ----------------------------------------------------------------------------
# Configuración general (ingreso mensual y si ya hizo el primer ingreso)
# ----------------------------------------------------------------------------
def leer_config(clave, por_defecto=None):
    with conectar() as con:
        fila = con.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
    return fila["valor"] if fila else por_defecto


def guardar_config(clave, valor):
    with conectar() as con:
        con.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, str(valor)),
        )


def esta_configurado():
    return leer_config("configurado") == "si"


def ingreso_mensual():
    return float(leer_config("ingreso_mensual", 0) or 0)


# ----------------------------------------------------------------------------
# Presupuestos
# ----------------------------------------------------------------------------
def guardar_presupuestos(limites: dict):
    """limites = {'Alimentación': 400000, 'Transporte': 150000, ...}"""
    with conectar() as con:
        for categoria, limite in limites.items():
            con.execute(
                "INSERT INTO presupuestos (categoria, limite_mensual) VALUES (?, ?) "
                "ON CONFLICT(categoria) DO UPDATE SET limite_mensual = excluded.limite_mensual",
                (categoria, float(limite)),
            )


def leer_presupuestos() -> dict:
    with conectar() as con:
        filas = con.execute("SELECT categoria, limite_mensual FROM presupuestos").fetchall()
    return {f["categoria"]: f["limite_mensual"] for f in filas}


# ----------------------------------------------------------------------------
# Movimientos
# ----------------------------------------------------------------------------
def _ahora_texto():
    """Hora de Colombia, igual que el resto de la app."""
    return datetime.now(ZONA).strftime("%Y-%m-%d %H:%M:%S")


def guardar_movimiento(fecha_hora, monto, tipo, descripcion, categoria_ia,
                       confianza, categoria_final, atipico=False, motivo_atipico=None):
    with conectar() as con:
        con.execute(
            """INSERT INTO movimientos
               (fecha_hora, monto, tipo_movimiento, descripcion, categoria_ia,
                confianza, categoria_final, atipico, motivo_atipico, actualizado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (fecha_hora, float(monto), tipo, descripcion.strip(), categoria_ia,
             float(confianza), categoria_final, int(bool(atipico)), motivo_atipico,
             _ahora_texto()),
        )


def leer_movimientos() -> pd.DataFrame:
    """Devuelve todos los movimientos como una tabla de pandas."""
    with conectar() as con:
        df = pd.read_sql_query("SELECT * FROM movimientos ORDER BY fecha_hora DESC", con)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df["atipico"] = df["atipico"].astype(bool)
    return df


def corregir_categoria(id_movimiento, nueva_categoria):
    with conectar() as con:
        con.execute(
            "UPDATE movimientos SET categoria_final = ?, actualizado_en = ? WHERE id = ?",
            (nueva_categoria, _ahora_texto(), int(id_movimiento)),
        )


def actualizar_movimiento(id_movimiento, fecha_hora, monto, descripcion, categoria_final,
                          atipico, motivo_atipico):
    """Edita un movimiento existente (la categoría propuesta por la IA no cambia)."""
    with conectar() as con:
        con.execute(
            """UPDATE movimientos
               SET fecha_hora = ?, monto = ?, descripcion = ?, categoria_final = ?,
                   atipico = ?, motivo_atipico = ?, actualizado_en = ?
               WHERE id = ?""",
            (fecha_hora, float(monto), descripcion.strip(), categoria_final,
             int(bool(atipico)), motivo_atipico, _ahora_texto(), int(id_movimiento)),
        )


def eliminar_movimiento(id_movimiento):
    with conectar() as con:
        con.execute("DELETE FROM movimientos WHERE id = ?", (int(id_movimiento),))


def version_datos():
    """
    Un "sello" que cambia cada vez que se agrega, corrige o borra un movimiento.
    La IA lo usa para saber si tiene que volver a aprender.
    """
    with conectar() as con:
        fila = con.execute(
            "SELECT COUNT(*) AS n, "
            "COALESCE(GROUP_CONCAT(id || ':' || categoria_final || ':' || monto || ':' "
            "|| fecha_hora || ':' || descripcion, '|'), '') AS sello "
            "FROM movimientos"
        ).fetchone()
    return (fila["n"], hash(fila["sello"]))


def borrar_todo():
    """Deja la base de datos vacía (para reiniciar el prototipo)."""
    with conectar() as con:
        con.executescript(
            "DELETE FROM movimientos; DELETE FROM presupuestos; DELETE FROM configuracion;"
        )
