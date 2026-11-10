# 💰 FinanzIA

**Tu asistente de finanzas personales con Inteligencia Artificial.**

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
| 🚨 **Gastos inusuales** | Avisa si un monto es mucho mayor (o menor) de lo normal para ese tipo de gasto. |

### ¿Cómo piensa la IA?

FinanzIA usa un modelo **KNN (K vecinos más cercanos)**. Para clasificar un movimiento
busca los **5 movimientos más parecidos** que conoce, teniendo en cuenta la
descripción, el monto, el tipo y la fecha y hora, y deja que "voten" por una categoría.

- **Es transparente:** te muestra esos 5 vecinos y las palabras que reconoció, para que sepas *por qué* eligió esa categoría.
- **Sabe cuándo dudar:** si no está segura (menos del 60% de los votos), te pide que elijas tú.
- **Aprende de ti:** cada movimiento que guardas o corriges se vuelve un nuevo ejemplo, sin reentrenar el modelo.
- **Mide su precisión real:** en el historial puedes ver qué porcentaje de veces no tuviste que corregirla.
- **Entiende con o sin tildes:** reconoce igual *"cafe"* y *"café"*.

---

## 🗂️ Estructura del proyecto

```
finanzia/
├── app.py                                   # Arranque: tema, datos y navegación (Streamlit)
├── vistas/                                  # Pantallas: bienvenida, inicio, registrar, movimientos, presupuesto
├── ui/                                      # Estilos, componentes, gráficos (Altair) y acceso a datos
├── assets/logo.svg                          # Logo de la app
├── .streamlit/config.toml                   # Tema claro y oscuro
├── modelo_ia.py                             # La IA: predicción, vecinos, gastos inusuales y aprendizaje
├── analisis.py                              # Cálculos: presupuesto, gastos hormiga, regla 50/30/20
├── base_datos.py                            # Base de datos SQLite (movimientos y presupuestos)
├── datos_demo.py                            # Movimientos de ejemplo para probar la app
├── ia_clasificadora_multivariable_knn.pkl   # Modelo de IA ya entrenado
├── requirements.txt                         # Librerías necesarias
└── README.md
```

La base de datos (`finanzia.db`) se crea sola la primera vez que abres la app.

**Tecnologías:** Python · Streamlit · scikit-learn · pandas · SQLite

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
2. Deja marcada la opción **"Cargar movimientos de ejemplo"** si quieres ver la app con datos.
3. Ve a **Registrar movimiento**, escribe un gasto y mira cómo lo clasifica la IA.

> Para empezar de cero, ve a **Presupuesto → Opciones del prototipo → Reiniciar prototipo**.

---

## 🚧 Limitaciones del prototipo

- El modelo se entrenó con **560 ejemplos**; puede equivocarse con descripciones poco comunes.
- Solo aprende **palabras nuevas** si se vuelve a entrenar; mientras tanto, se guía por el monto y la hora.
- Está pensada para **un solo usuario**: no tiene cuentas ni inicio de sesión.
- Los montos están en **pesos colombianos (COP)** y la hora es la de Colombia.

---

<details>
<summary>🔧 Notas técnicas (para desarrolladores)</summary>

- **`extraer_variables_temporales`:** el `.pkl` guarda solo el *nombre* de esta función,
  no su código, así que está reescrita en `modelo_ia.py`. Devuelve `hora`, `dia_semana`
  (0 = lunes), `dia_mes` y `es_fin_de_semana` (1 = viernes, sábado o domingo). Se
  verificó contra los datos guardados dentro del modelo.
- **Tildes:** el TF-IDF del modelo distingue "cafe" de "café". `MotorIA.normalizar_descripcion`
  cambia cada palabra desconocida por su versión con (o sin) tilde que sí está en el
  vocabulario. La descripción se guarda tal como la escribió el usuario.
- **Versión de scikit-learn:** si vuelven a entrenar el modelo, guárdenlo con la misma
  versión que aparece en `requirements.txt` (1.9.1).
- **Datos de ejemplo:** `datos_demo.py` ajusta los montos para que cada categoría quede
  en el 50% de su límite, según el presupuesto del usuario.
- **Streamlit Community Cloud:** se despliega con `app.py` como archivo principal y
  Python 3.12. El archivo SQLite se borra cada vez que la app se reinicia.

</details>
