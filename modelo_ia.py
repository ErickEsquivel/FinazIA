"""
modelo_ia.py
------------
Aquí vive la IA. Este archivo:

1. Carga el modelo entrenado (ia_clasificadora_multivariable_knn.pkl).
2. Predice la categoría de un movimiento nuevo y dice qué tan segura está.
3. Muestra los K "vecinos" (movimientos parecidos) que usó para decidir (K = 5).
4. Detecta si el movimiento es inusual comparando su monto con el de los 5
   movimientos con la descripción más parecida (vecinos buscados solo por
   texto y tipo, para que el monto no "se esconda" entre montos parecidos).
5. Aprende de los movimientos que el usuario confirma o corrige, sin reentrenar
   todo desde cero (KNN es un "aprendiz perezoso": basta con agregar los
   puntos nuevos al mapa).
"""

import sys

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors

from base_datos import CATEGORIAS_GASTO

# Si la categoría ganadora tiene menos de este porcentaje de los votos,
# la app le pide al usuario que elija en lugar de decidir sola.
UMBRAL_CONFIANZA = 0.60

# Un gasto se marca como inusual si su monto es al menos 4 veces la mediana
# de los montos de los 5 movimientos con descripción más parecida
# (y la diferencia supera $20.000).
VECES_MAYOR = 4
DIFERENCIA_MINIMA = 20_000
# ... o si es 20 veces menor (por ejemplo, olvidó escribir ceros).
VECES_MENOR = 20
# Cuántos movimientos parecidos se usan para comparar el monto
VECINOS_INUSUAL = 5
# Solo se juzga el monto si al menos 4 de esos 5 movimientos son de la misma
# categoría (si no coinciden, no sabe con qué comparar y prefiere no alertar).
# Ver notebooks/FinanzIA_analisis_modelo.ipynb, sección 4.5.
MINIMO_ACUERDO = 4

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ----------------------------------------------------------------------------
# 1. La función que usamos en el notebook para desglosar la fecha
#    (notebooks/FinanzIA_analisis_modelo.ipynb, sección 1).
#    El .pkl NO guarda el código de esta función, solo su nombre, así que hay
#    que volver a definirla aquí con el mismo nombre y el mismo resultado.
# ----------------------------------------------------------------------------
def extraer_variables_temporales(X):
    """Convierte la columna fecha_hora en 4 números: hora, día de la semana,
    día del mes y si es fin de semana (viernes, sábado o domingo)."""
    columna = X.iloc[:, 0] if isinstance(X, pd.DataFrame) else pd.Series(np.asarray(X).ravel())
    fechas = pd.to_datetime(columna)
    dia_semana = fechas.dt.dayofweek  # 0 = lunes ... 6 = domingo
    return pd.DataFrame({
        "hora": fechas.dt.hour.to_numpy(),
        "dia_semana": dia_semana.to_numpy(),
        "dia_mes": fechas.dt.day.to_numpy(),
        "es_fin_de_semana": (dia_semana >= 4).astype(int).to_numpy(),
    })


def cargar_pipeline(ruta_modelo):
    """Carga el .pkl. Antes, "presenta" la función anterior en el módulo
    principal (__main__), que es donde el notebook la tenía definida."""
    setattr(sys.modules["__main__"], "extraer_variables_temporales", extraer_variables_temporales)
    return joblib.load(ruta_modelo)


def _a_tabla(fechas, montos, tipos, descripciones):
    """Arma la tabla con las 4 columnas exactas que espera el modelo."""
    return pd.DataFrame({
        "fecha_hora": [pd.Timestamp(f).strftime("%Y-%m-%d %H:%M:%S") for f in fechas],
        "monto": [float(m) for m in montos],
        "tipo_movimiento": list(tipos),
        "descripcion_libre": [" ".join(str(d).split()) for d in descripciones],
    })


class MotorIA:
    """Envuelve el modelo KNN y le agrega las funciones útiles para la app."""

    def __init__(self, pipeline):
        self.preprocesador = pipeline.named_steps["preprocesador"]
        knn_base = pipeline.named_steps["clasificador"]
        self.parametros_knn = knn_base.get_params()

        # Los 560 puntos con los que se entrenó el modelo (ya transformados)
        self.X_base = sp.csr_matrix(knn_base._fit_X)
        self.y_base = knn_base.classes_[knn_base._y]
        self.n_base = self.X_base.shape[0]
        self.knn = knn_base

        # Datos para "traducir" un punto del mapa de vuelta a algo legible
        tfidf = self.preprocesador.named_transformers_["texto"]
        self.vocabulario = tfidf.get_feature_names_out()
        self.col_texto = self.X_base.shape[1] - len(self.vocabulario)  # = 6
        pesos = self.preprocesador.transformer_weights
        self.peso_tiempo, self.peso_monto, self.peso_tipo = pesos["tiempo"], pesos["numero"], pesos["tipo"]
        self.esc_tiempo = self.preprocesador.named_transformers_["tiempo"].named_steps["escalador_tiempo"]
        self.esc_monto = self.preprocesador.named_transformers_["numero"]

        # Montos reales de los puntos de entrenamiento (para detectar inusuales)
        self.montos_base = (self.X_base[:, 4].toarray().ravel() / self.peso_monto
                            * self.esc_monto.scale_[0] + self.esc_monto.mean_[0])
        # Máscara que apaga las columnas de tiempo (0-3) y monto (4): deja tipo y texto
        mascara = np.ones(self.X_base.shape[1]); mascara[:5] = 0
        self.solo_texto_y_tipo = sp.diags(mascara)

        # Movimientos del usuario que ya forman parte del "mapa"
        self.mov_usuario = pd.DataFrame()
        self.version = None

    # ------------------------------------------------------------------
    # Aprendizaje: agrega al mapa los movimientos confirmados por el usuario
    # ------------------------------------------------------------------
    def aprender(self, movimientos: pd.DataFrame, version):
        if version == self.version:
            return  # nada cambió desde la última vez
        if movimientos.empty:
            X, y = self.X_base, self.y_base
            montos = self.montos_base
            self.mov_usuario = pd.DataFrame()
        else:
            movimientos = movimientos.reset_index(drop=True)
            tabla = _a_tabla(movimientos["fecha_hora"], movimientos["monto"],
                             movimientos["tipo_movimiento"], movimientos["descripcion"])
            X_usuario = sp.csr_matrix(self.preprocesador.transform(tabla))
            X = sp.vstack([self.X_base, X_usuario]).tocsr()
            y = np.concatenate([self.y_base, movimientos["categoria_final"].to_numpy()])
            montos = np.concatenate([self.montos_base, movimientos["monto"].to_numpy(dtype=float)])
            self.mov_usuario = movimientos
        # Clasificador: todas las variables
        self.knn = KNeighborsClassifier(**self.parametros_knn).fit(X, y)
        # Buscador de inusuales: solo texto y tipo
        self.vecinos_monto = NearestNeighbors(n_neighbors=min(VECINOS_INUSUAL, X.shape[0])).fit(
            X @ self.solo_texto_y_tipo)
        self.montos = montos
        self.etiquetas = np.asarray(y)
        self.version = version

    @property
    def total_ejemplos(self):
        return self.n_base + len(self.mov_usuario)

    # ------------------------------------------------------------------
    # Predicción
    # ------------------------------------------------------------------
    def predecir(self, fecha_hora, monto, tipo, descripcion) -> dict:
        tabla = _a_tabla([fecha_hora], [monto], [tipo], [descripcion])
        x = sp.csr_matrix(self.preprocesador.transform(tabla))

        # Votos de los K vecinos (pesados por cercanía) para cada categoría
        probabilidades = dict(zip(self.knn.classes_, self.knn.predict_proba(x)[0]))

        # Un ingreso solo puede ser "Ingresos" y un gasto nunca puede serlo
        permitidas = ["Ingresos"] if tipo == "Ingreso" else CATEGORIAS_GASTO
        ranking = sorted(permitidas, key=lambda c: probabilidades.get(c, 0), reverse=True)
        sugerida = ranking[0]
        confianza = probabilidades.get(sugerida, 0.0)
        categoria_modelo = max(probabilidades, key=probabilidades.get)

        distancias, indices = self.knn.kneighbors(x)
        vecinos = [self._describir_vecino(i, d) for i, d in zip(indices[0], distancias[0])]

        texto = x[:, self.col_texto:]
        palabras = [self.vocabulario[j] for j in texto.indices if " " not in self.vocabulario[j]]

        indices_monto = self.vecinos_monto.kneighbors(x @ self.solo_texto_y_tipo, return_distance=False)[0]
        clases_parecidos = pd.Series(self.etiquetas[indices_monto])
        clase_comun, veces = clases_parecidos.value_counts().index[0], clases_parecidos.value_counts().iloc[0]
        montos_parecidos = self.montos[indices_monto][self.etiquetas[indices_monto] == clase_comun]
        atipico, motivos = self._revisar_atipico(monto, montos_parecidos, len(palabras) > 0,
                                                 veces >= MINIMO_ACUERDO)

        return {
            "categoria": sugerida,
            "confianza": float(confianza),
            # Si no reconoció ninguna palabra, mejor que el usuario confirme
            "segura": confianza >= UMBRAL_CONFIANZA and len(palabras) > 0,
            "categoria_modelo": categoria_modelo,
            "ranking": [(c, float(probabilidades.get(c, 0))) for c in ranking],
            "vecinos": vecinos,
            "palabras_reconocidas": palabras,
            "atipico": atipico,
            "motivo_atipico": " ".join(motivos) if motivos else None,
        }

    # ------------------------------------------------------------------
    # Traducir un vecino a algo que el usuario entienda
    # ------------------------------------------------------------------
    def _describir_vecino(self, indice, distancia) -> dict:
        if indice >= self.n_base:  # es un movimiento del propio usuario
            fila = self.mov_usuario.iloc[indice - self.n_base]
            fecha = pd.Timestamp(fila["fecha_hora"])
            return {
                "origen": "Tu historial",
                "descripcion": fila["descripcion"],
                "monto": float(fila["monto"]),
                "tipo": fila["tipo_movimiento"],
                "cuando": f"{DIAS[fecha.dayofweek]} {fecha.hour:02d}:00",
                "categoria": fila["categoria_final"],
                "distancia": float(distancia),
            }

        # Es un dato del entrenamiento: se "deshace" la escala para recuperar valores
        fila = self.X_base.getrow(indice).toarray().ravel()
        tiempo = fila[:4] / self.peso_tiempo * self.esc_tiempo.scale_ + self.esc_tiempo.mean_
        monto = fila[4] / self.peso_monto * self.esc_monto.scale_[0] + self.esc_monto.mean_[0]
        pesos_texto = fila[self.col_texto:]
        top = [self.vocabulario[j] for j in np.argsort(pesos_texto)[::-1][:6]
               if pesos_texto[j] > 0 and " " not in self.vocabulario[j]][:3]
        hora, dia = int(round(tiempo[0])), int(round(tiempo[1])) % 7
        return {
            "origen": "Entrenamiento",
            "descripcion": "palabras: " + ", ".join(top) if top else "(sin texto)",
            "monto": float(round(monto, -2)),
            "tipo": "Ingreso" if fila[5] > 0 else "Gasto",
            "cuando": f"{DIAS[dia]} {hora:02d}:00",
            "categoria": self.y_base[indice],
            "distancia": float(distancia),
        }

    # ------------------------------------------------------------------
    # Idea 4: ¿el movimiento es inusual?
    # ------------------------------------------------------------------
    def _revisar_atipico(self, monto, montos_parecidos, texto_conocido, hay_parecidos):
        # montos_parecidos: los de los movimientos con descripción parecida y de la misma categoría
        motivos = []
        mediana = float(np.median(montos_parecidos))
        # Solo compara montos si conoce movimientos con una descripción realmente parecida
        if texto_conocido and hay_parecidos and mediana > 0:
            veces = monto / mediana
            if veces >= VECES_MAYOR and monto - mediana >= DIFERENCIA_MINIMA:
                motivos.append(
                    f"El monto es {veces:.0f} veces mayor que el de los movimientos con "
                    f"descripción parecida (mediana ${mediana:,.0f}).".replace(",", ".")
                )
            elif veces <= 1 / VECES_MENOR:
                motivos.append(
                    f"El monto es mucho menor que el de los movimientos con descripción parecida "
                    f"(mediana ${mediana:,.0f}). ¿Te faltaron ceros?".replace(",", ".")
                )
        if not texto_conocido:
            motivos.append("La IA no reconoce ninguna palabra de la descripción, "
                           "así que solo pudo guiarse por el monto y la hora.")
        return (len(motivos) > 0), motivos
