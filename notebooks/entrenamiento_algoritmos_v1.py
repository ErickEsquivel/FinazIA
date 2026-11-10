import os
import time
import random
from datetime import datetime
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Importación de los 5 Algoritmos Clasificadores
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

# =====================================================================
# 1. CARGA O GENERACIÓN DEL DATASET DE 700 REGISTROS
# =====================================================================
archivo_csv = "dataset_multivariable_knn_vs_rf.csv"

if os.path.exists(archivo_csv):
    print(f"Cargando dataset existente desde '{archivo_csv}'...\n")
    df = pd.read_csv(archivo_csv)
else:
    print("Generando dataset sintético multivariable de 700 registros...\n")
    np.random.seed(42)
    random.seed(42)

    categorias_config = {
        "Alimentación": {
            "textos_claros": ["Mercado en el D1", "Compra en Ara", "Almuerzo corrientazo restaurante", "Mercado Éxito quincena", "Pollo asado almuerzo", "Verduras y frutas fruver", "Carne y pollo supermercado", "Desayuno panadería"],
            "tipo": "Gasto", "monto_rango": (14000, 280000), "horas": (7, 20), "dias": list(range(1, 29))
        },
        "Transporte": {
            "textos_claros": ["Recarga tarjeta Tullave Transmilenio", "Viaje en Uber al trabajo", "Carrera de taxi centro", "Gasolina moto estación Terpel", "Viaje en Didi", "Pasaje bus SITP", "Parqueadero centro comercial", "Mantenimiento aceite moto"],
            "tipo": "Gasto", "monto_rango": (3100, 55000), "horas": (5, 22), "dias": list(range(1, 29))
        },
        "Vivienda y Servicios": {
            "textos_claros": ["Pago arriendo apartamento", "Factura luz Enel Codensa", "Recibo agua Acueducto", "Factura internet hogar Claro", "Servicio gas natural Vanti", "Administración conjunto residencial", "Plan celular pospago Wom", "Cuota crédito hipotecario"],
            "tipo": "Gasto", "monto_rango": (45000, 1200000), "horas": (8, 18), "dias": [1, 2, 3, 5, 15, 16, 28, 30]
        },
        "Ocio y Entretenimiento": {
            "textos_claros": ["Entradas cine Cinecolombia", "Suscripción mensual Netflix", "Salida cervezas bar amigos", "Concierto boleta TuBoleta", "Suscripción Spotify Premium", "Compra videojuego Steam", "Rumba discoteca sábado", "Almuerzo especial fin de semana"],
            "tipo": "Gasto", "monto_rango": (18000, 220000), "horas": (18, 23), "dias": list(range(1, 29))
        },
        "Gastos Hormiga": {
            "textos_claros": ["Tinto y empanada esquina", "Papas paquetes y gaseosa", "Chicles y dulces tienda", "Café máquina universidad", "Postre helado Popsy", "Cigarrillos sueltos", "Agua en botella calle", "Mecato media tarde Oxxo"],
            "tipo": "Gasto", "monto_rango": (1500, 11000), "horas": (9, 19), "dias": list(range(1, 29))
        },
        "Salud y Educación": {
            "textos_claros": ["Compra medicamentos Cruz Verde", "Cita médica copago EPS", "Matrícula semestre universidad", "Curso programación online Udemy", "Fotocopias e impresiones estudio", "Consulta odontológica control", "Vitaminas droguería Cafam", "Libros técnicos ingeniería"],
            "tipo": "Gasto", "monto_rango": (12000, 650000), "horas": (8, 17), "dias": list(range(1, 29))
        },
        "Ingresos": {
            "textos_claros": ["Pago nómina quincenal empresa", "Transferencia mesada familiar", "Pago proyecto freelance ingeniería", "Abono intereses cuenta ahorros", "Venta artículo usado", "Reembolso gastos empresa", "Bono desempeño laboral", "Honorarios soporte técnico"],
            "tipo": "Ingreso", "monto_rango": (80000, 2800000), "horas": (8, 18), "dias": [1, 15, 16, 29, 30]
        }
    }

    textos_ambiguos_comunes = ["Pago por Nequi", "Compra en la tienda", "Transferencia bancaria", "Pago rápido"]
    datos = []

    for cat, cfg in categorias_config.items():
        for i in range(100):
            desc = random.choice(textos_ambiguos_comunes) if i < 15 else random.choice(cfg["textos_claros"])
            monto = round(random.uniform(*cfg["monto_rango"]), -2)
            dia = random.choice(cfg["dias"])
            hora = random.randint(*cfg["horas"])
            fecha_dt = datetime(2026, random.randint(1, 10), min(dia, 28), hora, random.randint(0, 59))
            datos.append({
                "descripcion_libre": desc,
                "tipo_movimiento": cfg["tipo"],
                "monto": monto,
                "fecha_hora": fecha_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "categoria": cat
            })
    df = pd.DataFrame(datos)

# Extraer variables de tiempo si no están aún como columnas separadas
df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
df["hora"] = df["fecha_hora"].dt.hour
df["dia_mes"] = df["fecha_hora"].dt.day
df["dia_semana"] = df["fecha_hora"].dt.weekday
df["es_fin_semana"] = (df["dia_semana"] >= 5).astype(int)

X = df[["descripcion_libre", "tipo_movimiento", "monto", "hora", "dia_mes", "dia_semana", "es_fin_semana"]]
y = df["categoria"]

# División estratificada: 80% entrenamiento (560 datos) y 20% prueba (140 datos -> 20 por categoría)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

# =====================================================================
# 2. PREPROCESADORES Y SISTEMA DE PESOS (transformer_weights)
# =====================================================================
pesos_columnas = {
    "texto": 3.0,   # Prioridad alta al significado de las palabras
    "tipo": 1.5,    # Muro divisor entre Ingreso y Gasto
    "monto": 0.6,   # Desempate por magnitud de dinero
    "tiempo": 0.25  # Contexto horario sutil
}

# Preprocesador estándar (para KNN, RF, SVM y Regresión Logística)
preprocesador_estandar = ColumnTransformer(
    transformers=[
        ("texto", TfidfVectorizer(ngram_range=(1, 2)), "descripcion_libre"),
        ("tipo", OneHotEncoder(handle_unknown="ignore"), ["tipo_movimiento"]),
        ("monto", StandardScaler(), ["monto"]),
        ("tiempo", StandardScaler(), ["hora", "dia_mes", "dia_semana", "es_fin_semana"])
    ],
    transformer_weights=pesos_columnas
)

# Preprocesador exclusivo para Naive Bayes (usa MinMaxScaler [0,1] porque MultinomialNB no admite números negativos)
preprocesador_nb = ColumnTransformer(
    transformers=[
        ("texto", TfidfVectorizer(ngram_range=(1, 2)), "descripcion_libre"),
        ("tipo", OneHotEncoder(handle_unknown="ignore"), ["tipo_movimiento"]),
        ("monto", MinMaxScaler(), ["monto"]),
        ("tiempo", MinMaxScaler(), ["hora", "dia_mes", "dia_semana", "es_fin_semana"])
    ],
    transformer_weights=pesos_columnas
)

# =====================================================================
# 3. CONFIGURACIÓN DE LOS 5 ALGORITMOS CLASIFICADORES
# =====================================================================
modelos = {
    "KNN": Pipeline([
        ("prep", preprocesador_estandar),
        ("clf", KNeighborsClassifier(n_neighbors=5, weights="distance", metric="euclidean"))
    ]),
    "Random Forest": Pipeline([
        ("prep", preprocesador_estandar),
        ("clf", RandomForestClassifier(n_estimators=100, max_depth=None, max_features="sqrt", criterion="gini", random_state=42))
    ]),
    "Support Vector Machines (SVM)": Pipeline([
        ("prep", preprocesador_estandar),
        ("clf", SVC(C=1.0, kernel="linear", random_state=42))
    ]),
    "Naive Bayes": Pipeline([
        ("prep", preprocesador_nb),
        ("clf", MultinomialNB(alpha=1.0))
    ]),
    "Regresión Logística": Pipeline([
        ("prep", preprocesador_estandar),
        ("clf", LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=1000, random_state=42))
    ])
}

# =====================================================================
# 4. ENTRENAMIENTO, REPORTE POR CATEGORÍA Y TABLA COMPARATIVA FINAL
# =====================================================================
tabla_comparativa = []

for nombre, pipeline in modelos.items():
    # Medir tiempo de entrenamiento
    inicio_train = time.perf_counter()
    pipeline.fit(X_train, y_train)
    tiempo_train_ms = (time.perf_counter() - inicio_train) * 1000

    # Medir tiempo de predicción
    inicio_pred = time.perf_counter()
    y_pred = pipeline.predict(X_test)
    tiempo_pred_ms = (time.perf_counter() - inicio_pred) * 1000

    # Calcular métricas globales
    acc = accuracy_score(y_test, y_pred) * 100
    prec = precision_score(y_test, y_pred, average="weighted") * 100
    rec = recall_score(y_test, y_pred, average="weighted") * 100
    f1 = f1_score(y_test, y_pred, average="weighted") * 100
    cv_mean = cross_val_score(pipeline, X, y, cv=5, scoring="accuracy").mean() * 100

    tabla_comparativa.append({
        "Algoritmo": nombre,
        "Accuracy (%)": round(acc, 2),
        "Precision (%)": round(prec, 2),
        "Recall (%)": round(rec, 2),
        "F1-Score (%)": round(f1, 2),
        "CV 5-Fold (%)": round(cv_mean, 2),
        "Tiempo Train (ms)": round(tiempo_train_ms, 2),
        "Tiempo Pred (ms)": round(tiempo_pred_ms, 2)
    })

    # Imprimir reporte detallado de cada algoritmo (Precision, Recall, F1-Score por categoría)
    print("=" * 75)
    print(f" REPORTE DETALLADO POR CATEGORÍA: {nombre.upper()}")
    print("=" * 75)
    print(classification_report(y_test, y_pred, digits=2))

# Imprimir Tabla Resumen Global al final
df_comparativa = pd.DataFrame(tabla_comparativa)
print("\n" + "=" * 105)
print(" TABLA COMPARATIVA GLOBAL DE RESULTADOS (5 ALGORITMOS CLASIFICADORES)")
print("=" * 105)
print(df_comparativa.to_string(index=False))
print("=" * 105)