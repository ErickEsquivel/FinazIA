"""
entrenamiento.py
----------------
Entrena y evalúa el modelo de FinanzIA con la división 70 / 10 / 20
(la misma metodología de notebooks/FinanzIA_analisis_modelo.ipynb, sección 2.4).

    70 % entrenamiento → el modelo aprende de estos ejemplos.
    10 % ajuste        → se escogen hiperparámetros sin tocar la prueba.
    20 % prueba        → se mide el resultado final UNA sola vez.

La división es AGRUPADA por "frase base" y ESTRATIFICADA por clase: todas las
variantes de una frase ("tinto con nequi", "tinto hoy"...) quedan en el mismo
conjunto, así la prueba solo tiene frases que el modelo nunca vio. Como un solo
10 % es muy poco (≈70 filas), el ajuste se repite en 8 rondas rotando qué parte
del 80 % de desarrollo hace de ajuste, y se promedia.

Uso:
    python entrenamiento.py                    # evalúa y guarda datos/reporte_modelo.json
    python entrenamiento.py --guardar-modelo   # además reemplaza el .pkl de la app
    python entrenamiento.py --rapido           # sin comparar los otros 4 algoritmos

La app (pantalla «Modelo») muestra el reporte que genera este script.
"""

import argparse
import json
import re
import time
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
                             precision_score, recall_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.svm import SVC

from base_datos import CATEGORIAS
# La app carga el .pkl con esta misma función (joblib guarda su nombre, no su código)
from modelo_ia import UMBRAL_CONFIANZA, extraer_variables_temporales

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent
RUTA_DATOS = RAIZ / "datos" / "dataset_multivariable.csv"
RUTA_EXTERNA = RAIZ / "datos" / "prueba_externa.csv"
RUTA_REPORTE = RAIZ / "datos" / "reporte_modelo.json"
RUTA_MODELO = RAIZ / "ia_clasificadora_multivariable_knn.pkl"

SEMILLA = 42
COLUMNAS_X = ["fecha_hora", "monto", "tipo_movimiento", "descripcion_libre"]
N_BLOQUES = 10           # 10 bloques de 10 %: 2 para prueba (20 %), 8 para desarrollo (80 %)
BLOQUES_PRUEBA = 2

# Grilla de KNN (sección 3.3 del notebook)
VALORES_K = [3, 5, 7, 9, 11]
PESOS_MONTO = [0.6, 1.0, 2.0, 3.0]
PESOS_TIEMPO = [0.25, 0.5, 1.0]
PESO_TEXTO, PESO_TIPO = 3.0, 1.5
# K del modelo del equipo: con pocos datos K = 3 aprende un poco más de una sola
# corrección, pero un K mayor es más estable a medida que crecen los datos.
K_EQUIPO = 5

GRILLAS_OTROS = {
    "Random Forest": [dict(n_estimators=n, max_depth=d, min_samples_leaf=l)
                      for n in [100, 300] for d in [None, 10] for l in [1, 2]],
    "SVM": [dict(kernel=k, C=c) for k in ["linear", "rbf"] for c in [0.1, 1, 10]],
    "Naive Bayes": [dict(alpha=a) for a in [0.01, 0.1, 0.5, 1.0]],
    "Reg. Logística": [dict(C=c) for c in [0.1, 1, 10, 100]],
}
MODELOS = ["KNN", "Random Forest", "SVM", "Naive Bayes", "Reg. Logística"]


# ----------------------------------------------------------------------------
# Datos y grupos
# ----------------------------------------------------------------------------
SUFIJOS = ["con nequi", "por pse", "pago rapido", "en efectivo", "hoy"]


def frase_base(texto: str) -> str:
    """'Recarga tarjeta SITP por PSE' y 'recarga tarjeta sitp hoy' -> 'recarga tarjeta sitp'."""
    t = unicodedata.normalize("NFKD", str(texto).lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"\s+", " ", t).strip()
    cambio = True
    while cambio:
        cambio = False
        for s in SUFIJOS:
            if t.endswith(" " + s):
                t, cambio = t[: -len(s) - 1].strip(), True
    return t


def cargar_datos(ruta=RUTA_DATOS) -> pd.DataFrame:
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


# ----------------------------------------------------------------------------
# División 70 / 10 / 20
# ----------------------------------------------------------------------------
def dividir_70_10_20(X, y, grupos, semilla=SEMILLA):
    """
    Devuelve (idx_prueba, idx_desarrollo, rondas_ajuste).
      - idx_prueba: 20 % (2 de 10 bloques), frases base que nunca se ven al entrenar.
      - idx_desarrollo: el 80 % restante (entrenamiento + ajuste).
      - rondas_ajuste: 8 pares (idx_entrenamiento 70 %, idx_ajuste 10 %) dentro del desarrollo.
    """
    bloques = [va for _, va in
               StratifiedGroupKFold(n_splits=N_BLOQUES, shuffle=True, random_state=semilla).split(X, y, grupos)]
    idx_prueba = np.concatenate(bloques[:BLOQUES_PRUEBA])
    idx_desarrollo = np.setdiff1d(np.arange(len(X)), idx_prueba)
    rondas = [(np.concatenate([bloques[j] for j in range(BLOQUES_PRUEBA, N_BLOQUES) if j != i]), bloques[i])
              for i in range(BLOQUES_PRUEBA, N_BLOQUES)]
    return idx_prueba, idx_desarrollo, rondas


# ----------------------------------------------------------------------------
# Modelos (misma estructura que el .pkl que carga la app)
# ----------------------------------------------------------------------------
def construir_preprocesador(pesos, para_naive_bayes=False):
    Escalador = MinMaxScaler if para_naive_bayes else StandardScaler
    return ColumnTransformer(
        transformers=[
            ("tiempo", Pipeline([("extractor", FunctionTransformer(extraer_variables_temporales)),
                                 ("escalador_tiempo", Escalador())]), ["fecha_hora"]),
            ("numero", Escalador(), ["monto"]),
            ("tipo", OneHotEncoder(drop="if_binary"), ["tipo_movimiento"]),
            ("texto", TfidfVectorizer(ngram_range=(1, 2)), "descripcion_libre"),
        ],
        transformer_weights=pesos,
    )


def crear(nombre, pesos, **hp):
    clasificadores = {
        "KNN": lambda: KNeighborsClassifier(**{"n_neighbors": 5, "weights": "distance", "metric": "euclidean", **hp}),
        "Random Forest": lambda: RandomForestClassifier(random_state=SEMILLA, **hp),
        "SVM": lambda: SVC(**{"kernel": "linear", **hp}),
        "Naive Bayes": lambda: MultinomialNB(**hp),
        "Reg. Logística": lambda: LogisticRegression(max_iter=2000, **hp),
    }
    return Pipeline([("preprocesador", construir_preprocesador(pesos, nombre == "Naive Bayes")),
                     ("clasificador", clasificadores[nombre]())])


def pesos_knn(monto, tiempo):
    return {"texto": PESO_TEXTO, "tipo": PESO_TIPO, "numero": float(monto), "tiempo": float(tiempo)}


def f1_ajuste(fabricar, X, y, rondas) -> float:
    """Promedio del F1 macro en las 8 rondas (entrena con 70 %, evalúa en 10 %)."""
    puntajes = []
    for tr, va in rondas:
        modelo = fabricar().fit(X.iloc[tr], y.iloc[tr])
        puntajes.append(f1_score(y.iloc[va], modelo.predict(X.iloc[va]), average="macro"))
    return float(np.mean(puntajes))


# ----------------------------------------------------------------------------
# Segundo criterio de la app: aprender con UNA corrección del usuario
# ----------------------------------------------------------------------------
FRASES_PERSONALES = [  # (descripción, monto, tipo, clase que asigna el usuario, hora)
    ("Pago a doña Rosa", 12000, "Gasto", "Alimentación", 13),
    ("Transferencia a Camilo", 450000, "Gasto", "Vivienda y Servicios", 10),
    ("Pago al profe Andrés", 80000, "Gasto", "Salud y Educación", 17),
    ("Plata para el Chino", 8000, "Gasto", "Gastos Hormiga", 15),
    ("Pago a don Jaime", 5000, "Gasto", "Transporte", 7),
    ("Pago de la tía Marta", 300000, "Ingreso", "Ingresos", 10),
    ("Cuota del parche", 60000, "Gasto", "Ocio y Entretenimiento", 21),
    ("Pago a Luisa", 250000, "Gasto", "Vivienda y Servicios", 9),
    ("Vaca donde Pipe", 35000, "Gasto", "Ocio y Entretenimiento", 20),
    ("Pago donde Mono", 9000, "Gasto", "Gastos Hormiga", 16),
    ("Pago a la señora del almuerzo", 13000, "Gasto", "Alimentación", 12),
    ("Pago al tutor de inglés", 70000, "Gasto", "Salud y Educación", 18),
]
VARIACIONES = [(1.3, +2, "2026-11-28"), (0.6, -3, "2026-11-04"), (2.0, +4, "2026-11-22")]  # otro monto, hora y día


def _movimiento(desc, monto, tipo, hora, fecha="2026-11-11"):
    return pd.DataFrame([{"fecha_hora": pd.Timestamp(f"{fecha} {min(max(hora, 0), 23):02d}:00"),
                          "monto": monto, "tipo_movimiento": tipo, "descripcion_libre": desc}])


CORREGIDOS = pd.concat([_movimiento(d, m, t, h) for d, m, t, c, h in FRASES_PERSONALES], ignore_index=True)
ETIQUETAS_CORR = pd.Series([c for d, m, t, c, h in FRASES_PERSONALES])
SIGUIENTE_VEZ = pd.concat([_movimiento(d, round(m * f, -2), t, h + dh, fecha)
                           for d, m, t, c, h in FRASES_PERSONALES for f, dh, fecha in VARIACIONES], ignore_index=True)
ESPERADO = np.array([c for d, m, t, c, h in FRASES_PERSONALES for _ in VARIACIONES])


def aprende_con_una_correccion(fabricar, X_dev, y_dev) -> int:
    """Entrena con el 80 % + las 12 correcciones; cuenta aciertos en las 36 pruebas."""
    modelo = fabricar().fit(pd.concat([X_dev, CORREGIDOS], ignore_index=True),
                            pd.concat([y_dev, ETIQUETAS_CORR], ignore_index=True))
    return int((modelo.predict(SIGUIENTE_VEZ) == ESPERADO).sum())


def predecir_como_app(modelo, datos):
    """Igual que la app: un ingreso solo puede ser "Ingresos" y un gasto nunca lo es."""
    puntajes = modelo.predict_proba if hasattr(modelo, "predict_proba") else modelo.decision_function
    P = pd.DataFrame(puntajes(datos[COLUMNAS_X]), columns=modelo.classes_, index=datos.index)
    es_ingreso = (datos["tipo_movimiento"] == "Ingreso").to_numpy()
    P.loc[es_ingreso, [c for c in P.columns if c != "Ingresos"]] = -np.inf
    P.loc[~es_ingreso, "Ingresos"] = -np.inf
    return P.idxmax(axis=1).to_numpy(), P.max(axis=1).to_numpy()


def metricas(y_real, y_pred) -> dict:
    acc = accuracy_score(y_real, y_pred)
    return {"accuracy": float(acc), "error": float(1 - acc),
            "precision": float(precision_score(y_real, y_pred, average="macro", zero_division=0)),
            "recall": float(recall_score(y_real, y_pred, average="macro", zero_division=0)),
            "f1": float(f1_score(y_real, y_pred, average="macro", zero_division=0))}


# ----------------------------------------------------------------------------
# Proceso completo
# ----------------------------------------------------------------------------
def entrenar_y_evaluar(comparar=True, guardar_modelo=False, decir=print) -> dict:
    inicio = time.perf_counter()
    df = cargar_datos()
    df["frase_base"] = df["descripcion_libre"].map(frase_base)
    X, y, grupos = df[COLUMNAS_X], df["categoria"], df["frase_base"]

    # 1) División 70 / 10 / 20 -------------------------------------------------
    idx_prueba, idx_dev, rondas = dividir_70_10_20(X, y, grupos)
    X_dev, y_dev = X.iloc[idx_dev], y.iloc[idx_dev]
    X_prueba, y_prueba = X.iloc[idx_prueba], y.iloc[idx_prueba]
    fuga = bool(set(grupos.iloc[idx_prueba]) & set(grupos.iloc[idx_dev]))
    n = len(X)
    decir(f"Datos: {n} movimientos, {grupos.nunique()} frases base")
    decir(f"Prueba: {len(idx_prueba)} ({len(idx_prueba) / n:.0%}) · desarrollo: {len(idx_dev)} "
          f"({len(idx_dev) / n:.0%}) · ¿frases de prueba vistas al entrenar? {'sí' if fuga else 'no'}")

    division = {
        "total": n, "frases_base": int(grupos.nunique()),
        "prueba": {"filas": int(len(idx_prueba)), "frases_base": int(grupos.iloc[idx_prueba].nunique()),
                   "por_clase": {k: int(v) for k, v in y_prueba.value_counts().items()}},
        "desarrollo": {"filas": int(len(idx_dev)), "frases_base": int(grupos.iloc[idx_dev].nunique())},
        "rondas": [{"entrenamiento": int(len(tr)), "ajuste": int(len(va))} for tr, va in rondas],
        "fuga": fuga,
    }

    # 2) Ajuste de KNN con el 10 % (8 rondas) ---------------------------------
    decir(f"Ajuste de KNN: {len(VALORES_K) * len(PESOS_MONTO) * len(PESOS_TIEMPO)} configuraciones × {len(rondas)} rondas…")
    grilla = []
    for k in VALORES_K:
        for w_monto in PESOS_MONTO:
            for w_tiempo in PESOS_TIEMPO:
                fab = lambda: crear("KNN", pesos_knn(w_monto, w_tiempo), n_neighbors=k)
                grilla.append({"k": k, "peso_monto": w_monto, "peso_tiempo": w_tiempo,
                               "f1_ajuste": f1_ajuste(fab, X, y, rondas),
                               "aprende_correccion": aprende_con_una_correccion(fab, X_dev, y_dev)})
    grilla_df = pd.DataFrame(grilla)
    total_corr = len(ESPERADO)
    candidatas = grilla_df[grilla_df["aprende_correccion"] == total_corr].sort_values("f1_ajuste", ascending=False)
    base = candidatas.iloc[0] if not candidatas.empty else grilla_df.sort_values("f1_ajuste", ascending=False).iloc[0]
    elegida = grilla_df[(grilla_df["k"] == K_EQUIPO) & (grilla_df["peso_monto"] == base["peso_monto"])
                        & (grilla_df["peso_tiempo"] == base["peso_tiempo"])].iloc[0]
    k_final = int(elegida["k"])
    pesos_finales = pesos_knn(elegida["peso_monto"], elegida["peso_tiempo"])
    decir(f"Elegido: K = {k_final}, pesos = {pesos_finales} (F1 ajuste {elegida['f1_ajuste']:.1%}, "
          f"aprende {int(elegida['aprende_correccion'])}/{total_corr})")

    # 3) Prueba (20 %), una sola vez -------------------------------------------
    knn_dev = crear("KNN", pesos_finales, n_neighbors=k_final).fit(X_dev, y_dev)
    pred = knn_dev.predict(X_prueba)
    prueba = metricas(y_prueba, pred)
    clases = [c for c in CATEGORIAS if c in set(y)]
    p, r, f, s = precision_recall_fscore_support(y_prueba, pred, labels=clases, zero_division=0)
    por_clase = [{"clase": c, "precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "soporte": int(s[i])}
                 for i, c in enumerate(clases)]
    matriz = confusion_matrix(y_prueba, pred, labels=clases).tolist()
    proba = knn_dev.predict_proba(X_prueba)
    conf = proba.max(1)
    acierto = knn_dev.classes_[proba.argmax(1)] == y_prueba.to_numpy()
    alta = conf >= UMBRAL_CONFIANZA
    confianza = {"umbral": UMBRAL_CONFIANZA,
                 "pct_alta": float(alta.mean()), "acierto_alta": float(acierto[alta].mean()) if alta.any() else None,
                 "pct_baja": float((~alta).mean()), "acierto_baja": float(acierto[~alta].mean()) if (~alta).any() else None}
    decir(f"Prueba (20 %): accuracy {prueba['accuracy']:.1%} · F1 macro {prueba['f1']:.1%}")

    # 4) Modelo final con el 100 % y prueba externa ---------------------------
    modelo_final = crear("KNN", pesos_finales, n_neighbors=k_final).fit(X, y)
    externa = None
    if RUTA_EXTERNA.exists():
        ext = cargar_datos(RUTA_EXTERNA)
        pred_ext, conf_ext = predecir_como_app(modelo_final, ext)
        externa = {"filas": int(len(ext)), **metricas(ext["categoria"], pred_ext)}
        decir(f"Prueba externa ({len(ext)} frases redactadas aparte): accuracy {externa['accuracy']:.1%}")

    # 5) Comparación con los otros algoritmos (mismo 70/10/20) ----------------
    comparacion = []
    if comparar:
        hiper = {"KNN": dict(n_neighbors=k_final)}
        for nombre, opciones in GRILLAS_OTROS.items():
            decir(f"Ajustando {nombre} ({len(opciones)} configuraciones × {len(rondas)} rondas)…")
            resultados = [(f1_ajuste(lambda: crear(nombre, pesos_finales, **hp), X, y, rondas), hp) for hp in opciones]
            hiper[nombre] = max(resultados, key=lambda t: t[0])[1]
        for nombre in MODELOS:
            fab = lambda: crear(nombre, pesos_finales, **hiper[nombre])
            t0 = time.perf_counter(); m_dev = fab().fit(X_dev, y_dev); t_train = (time.perf_counter() - t0) * 1000
            fila = {"modelo": nombre, "hiperparametros": {k: v for k, v in hiper[nombre].items()},
                    "f1_ajuste": f1_ajuste(fab, X, y, rondas), **metricas(y_prueba, m_dev.predict(X_prueba)),
                    "entrenar_ms": t_train,
                    "aprende_correccion": aprende_con_una_correccion(fab, X_dev, y_dev)}
            if RUTA_EXTERNA.exists():
                fila["externa"] = float(accuracy_score(ext["categoria"], predecir_como_app(fab().fit(X, y), ext)[0]))
            comparacion.append(fila)

    # 6) Guardar ----------------------------------------------------------------
    if guardar_modelo:
        joblib.dump(modelo_final, RUTA_MODELO)
        decir(f"Modelo guardado en {RUTA_MODELO.name}")

    reporte = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "scikit_learn": sklearn.__version__,
        "semilla": SEMILLA,
        "division": division,
        "ajuste": {"metrica": "F1 macro promedio en 8 rondas (70 % / 10 %)",
                   "grilla_knn": grilla_df.to_dict(orient="records"),
                   "total_correcciones": total_corr},
        "modelo": {"algoritmo": "KNN", "k": k_final, "weights": "distance", "metric": "euclidean",
                   "pesos": pesos_finales, "f1_ajuste": float(elegida["f1_ajuste"]),
                   "aprende_correccion": int(elegida["aprende_correccion"])},
        "prueba": {**prueba, "por_clase": por_clase, "clases": clases, "matriz": matriz, "confianza": confianza},
        "externa": externa,
        "comparacion": comparacion,
        "segundos": round(time.perf_counter() - inicio, 1),
    }
    RUTA_REPORTE.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    decir(f"Reporte guardado en datos/{RUTA_REPORTE.name} ({reporte['segundos']} s)")
    return reporte


def leer_reporte():
    """Reporte de la última ejecución, o None si todavía no existe."""
    if not RUTA_REPORTE.exists():
        return None
    return json.loads(RUTA_REPORTE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrena y evalúa FinanzIA con la división 70/10/20.")
    parser.add_argument("--guardar-modelo", action="store_true",
                        help="reemplaza ia_clasificadora_multivariable_knn.pkl con el modelo entrenado con el 100 %%")
    parser.add_argument("--rapido", action="store_true", help="no compara con los otros 4 algoritmos")
    args = parser.parse_args()
    entrenar_y_evaluar(comparar=not args.rapido, guardar_modelo=args.guardar_modelo)
