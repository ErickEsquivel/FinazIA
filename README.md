# 💰 FinanzIA

**Tu asistente de finanzas personales con Inteligencia Artificial**, pensado para
estudiantes y personas con ingresos variables.

> ⚠️ **Esto es un prototipo, no una versión final.** FinanzIA se desarrolló como
> proyecto académico para demostrar cómo un modelo de IA puede ayudar a manejar
> el dinero del día a día. Puede tener errores, sus datos de entrenamiento son
> limitados y no reemplaza la asesoría de un profesional en finanzas.

## 🚀 Pruébalo en línea

👉 **[https://proyecto-ia-finaz.streamlit.app/](https://proyecto-ia-finaz.streamlit.app/)**

No necesitas instalar nada. Al entrar por primera vez puedes cargar **movimientos
de ejemplo** para explorar la app con un mes de datos ya registrado.

> En la versión en línea, los datos son compartidos y se borran cada vez que la
> app se reinicia. No registres información personal real.

- **Análisis y justificación del modelo:** [`notebooks/FinanzIA_analisis_modelo.ipynb`](notebooks/FinanzIA_analisis_modelo.ipynb)
  · [Abrir en Colab](https://colab.research.google.com/github/ErickEsquivel/FinazIA/blob/main/notebooks/FinanzIA_analisis_modelo.ipynb)

---

## 📖 ¿Qué es FinanzIA?

Registrar los gastos es aburrido, y casi nadie sabe en qué se le va la plata.
FinanzIA lo hace más fácil: **tú escribes el movimiento como lo dirías normalmente**
(por ejemplo, *"tinto en la chaza"* o *"Uber a la universidad"*) y una **IA lo
clasifica sola** en una de estas categorías:

`Alimentación` · `Transporte` · `Vivienda y Servicios` · `Ocio y Entretenimiento` ·
`Gastos Hormiga` · `Salud y Educación` · `Ingresos`

Con esa categoría, la app te ayuda a tomar mejores decisiones:

| Función | Qué hace |
|---|---|
| 🔔 **Alertas de presupuesto** | Al registrar un gasto te dice cuánto te queda del límite de esa categoría, o si ya lo superaste. |
| 🐜 **Detector de gastos hormiga** | Muestra cuánto se te va en gastos pequeños (tintos, dulces, paquetes), cuáles repites más y cuánto sumarían en un año. |
| 📊 **Regla 50/30/20** | Compara tus gastos con la recomendación: 50% necesidades, 30% deseos y 20% ahorro. |
| 🚨 **Gastos inusuales** | Avisa si un monto es mucho mayor (o menor) que el de movimientos con una descripción parecida. |

### ¿Cómo piensa la IA?

FinanzIA usa un modelo **KNN (K vecinos más cercanos)**. Para clasificar un movimiento
busca los **5 movimientos más parecidos** que conoce, teniendo en cuenta la
descripción, el monto, el tipo y la fecha y hora, y deja que "voten" por una categoría.

- **Es transparente:** te muestra esos 5 vecinos y las palabras que reconoció, para que sepas *por qué* eligió esa categoría.
- **Sabe cuándo dudar:** si no está segura (menos del 60% de los votos), te pide que elijas tú.
- **Aprende de ti:** cada movimiento que guardas o corriges se vuelve un nuevo ejemplo, sin reentrenar el modelo.
- **Mide su precisión real:** en Movimientos puedes ver qué porcentaje de veces no tuviste que corregirla.
- **Detecta inusuales con cuidado:** compara el monto con los 5 movimientos de descripción
  más parecida, y solo avisa si al menos 4 de ellos son de la misma categoría.

### El modelo en una tabla

| | |
|---|---|
| Tipo de problema | Clasificación supervisada multiclase (7 clases) |
| Variable objetivo | `categoria` |
| Características | `descripcion_libre` (TF-IDF 1-2 gramas), `tipo_movimiento` (one-hot), `monto` (estandarizado), `fecha_hora` → hora, día de la semana, día del mes, fin de semana (estandarizados) |
| Algoritmo | KNN, K = 5, distancia euclidiana ponderada por cercanía |
| Pesos por bloque | texto 3.0 · tipo 1.5 · monto 2.0 · tiempo 0.5 |
| Datos | 700 movimientos sintéticos, 100 por clase, 126 frases base |
| División | 70 % entrenamiento · 10 % ajuste (8 rondas) · 20 % prueba, agrupada por frase base |

| Evaluación | KNN | Random Forest | SVM | Naive Bayes | Reg. Logística |
|---|---|---|---|---|---|
| Versión 1: división aleatoria (con fuga) | 96.4 % | 95.7 % | 97.1 % | 97.9 % | 97.1 % |
| Prueba 20 %, frases nunca vistas | 63.6 % | 79.3 % | 72.9 % | 66.4 % | 72.9 % |
| Prueba externa (70 frases redactadas aparte) | 78.6 % | 71.4 % | 77.1 % | 72.9 % | **80.0 %** |
| Aprende con una sola corrección (de 36) | 29 | 28 | 36 | 36 | 36 |

Por qué KNN, el ajuste de hiperparámetros, BoW vs. TF-IDF, la fuga de información
y la detección de inusuales están explicados en el notebook.

---

## 🗂️ Estructura del proyecto

```
finazia/
├── app.py                                   # Arranque: tema, datos y navegación (Streamlit)
├── vistas/                                  # Pantallas: bienvenida, inicio, registrar, movimientos, presupuesto
├── ui/                                      # Estilos, componentes, gráficos (Altair) y acceso a datos
├── assets/logo.svg                          # Logo de la app
├── .streamlit/config.toml                   # Tema claro y oscuro
├── modelo_ia.py                             # Carga del modelo, predicción, vecinos, inusuales, aprendizaje
├── analisis.py                              # Cálculos: presupuesto, hormiga, 50/30/20, precisión real
├── base_datos.py                            # Todo lo de SQLite
├── datos_demo.py                            # Movimientos de ejemplo para la demo
├── ia_clasificadora_multivariable_knn.pkl   # Modelo entrenado (lo genera el notebook)
├── requirements.txt
├── datos/
│   ├── dataset_multivariable.csv            # 700 movimientos etiquetados (entrenamiento)
│   ├── prueba_externa.csv                   # 70 movimientos redactados aparte (solo evaluación)
│   └── plantilla_registros_reales.csv       # Plantilla para registrar movimientos reales
└── notebooks/
    ├── FinanzIA_analisis_modelo.ipynb       # Análisis completo y entrenamiento del modelo final
    └── entrenamiento_algoritmos_v1.py       # Primera comparación de los 5 algoritmos (versión anterior)
```

La base de datos (`finanzia.db`) se crea sola la primera vez que abres la app.

**Tecnologías:** Python · Streamlit · scikit-learn · pandas · Altair · SQLite

---

## 💻 Instalarlo y correrlo en tu computador

**Necesitas:** [Python 3.12](https://www.python.org/downloads/) y [Git](https://git-scm.com/).

**1. Descarga el proyecto**

```bash
git clone https://github.com/ErickEsquivel/FinazIA.git
cd FinazIA
```

**2. Crea un entorno virtual** (recomendado, para no mezclar librerías)

```bash
python -m venv venv
```

Actívalo:

- **Windows:** `venv\Scripts\activate`
- **Mac / Linux:** `source venv/bin/activate`

**3. Instala las librerías**

```bash
pip install -r requirements.txt
```

**4. Ejecuta la app**

```bash
streamlit run app.py
```

Se abrirá sola en tu navegador en **http://localhost:8501**.

**5. Primeros pasos**

1. Escribe tu ingreso mensual aproximado. La app te propone un límite para cada categoría.
2. Deja activada la opción **"Cargar movimientos de ejemplo"** si quieres ver la app con datos.
3. Ve a **Registrar**, escribe un gasto y mira cómo lo clasifica la IA.

> Para empezar de cero, ve a **Presupuesto → Ajustes → Reiniciar la app**.

---

## 🔁 Volver a entrenar el modelo

1. Abran el notebook en Colab (enlace arriba) o en Jupyter y ejecuten todas las celdas.
2. La última sección guarda `ia_clasificadora_multivariable_knn.pkl`.
3. Copien ese archivo a la raíz del repositorio (reemplazando el anterior).

Usen la misma versión de scikit-learn que está en `requirements.txt` (1.9.1).

---

## 🚧 Limitaciones del prototipo

- El modelo se entrenó con **700 ejemplos sintéticos**; puede equivocarse con descripciones poco comunes.
- Solo aprende **palabras nuevas** si se vuelve a entrenar; mientras tanto, se guía por el monto y la hora.
- Distingue palabras con y sin tilde (*"cafe"* y *"café"* son distintas para el modelo).
- Está pensada para **un solo usuario**: no tiene cuentas ni inicio de sesión.
- Los montos están en **pesos colombianos (COP)** y la hora es la de Colombia.

---

<details>
<summary>🔧 Notas técnicas (para desarrolladores)</summary>

- **`extraer_variables_temporales`:** el `.pkl` guarda solo el *nombre* de esta función,
  no su código, así que está reescrita en `modelo_ia.py` con el mismo resultado que en el
  notebook. Devuelve `hora`, `dia_semana` (0 = lunes), `dia_mes` y `es_fin_de_semana`.
- **Inusuales:** se buscan los 5 movimientos más parecidos usando solo texto y tipo
  (sin monto ni hora), para que el monto no "se esconda" entre montos parecidos.
- **Datos de ejemplo:** `datos_demo.py` carga un mes típico con montos fijos. Si el mes
  va empezando, los comprime en los días que ya pasaron.
- **Streamlit Community Cloud:** se despliega con `app.py` como archivo principal y
  Python 3.12. El archivo SQLite se borra cada vez que la app se reinicia.

</details>
