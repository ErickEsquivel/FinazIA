# FinanzIA: prototipo con Streamlit + SQLite

Aplicación para manejar finanzas personales. La IA (KNN) clasifica cada
movimiento y esa categoría se usa para alertar, calcular y aconsejar.

## Estructura

```
finanzia/
├── app.py                                   # Interfaz (pantallas de Streamlit)
├── modelo_ia.py                             # Carga del modelo, predicción, vecinos, inusuales, aprendizaje
├── analisis.py                              # Cálculos: presupuesto, hormiga, 50/30/20, precisión real
├── base_datos.py                            # Todo lo de SQLite
├── datos_demo.py                            # Movimientos de ejemplo para la demo
├── ia_clasificadora_multivariable_knn.pkl   # Su modelo entrenado
├── requirements.txt
└── .gitignore
```

La base de datos `finanzia.db` se crea sola la primera vez que se abre la app.

## Ejecutarla en el computador

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador (http://localhost:8501).

## Subirla a Streamlit Community Cloud

1. Suban la carpeta a un repositorio de GitHub (el `.gitignore` evita subir la base de datos).
2. En https://share.streamlit.io, elijan **Create app**, el repositorio y `app.py` como archivo principal.
3. En **Advanced settings**, elijan **Python 3.12**.
4. Desplieguen.

**Importante:** en Streamlit Cloud el archivo SQLite se borra cada vez que la app
se reinicia o se vuelve a desplegar. Para un prototipo está bien; antes de la
sustentación usen el botón de datos de ejemplo (en la bienvenida o en
Presupuesto → Opciones del prototipo).

## Las 4 ideas y dónde están en el código

| Idea | Qué hace | Dónde |
|---|---|---|
| 1. Alertas al registrar | Al elegir la categoría, dice cuánto del límite queda o si se pasó | `analisis.alerta_registro`, pantalla Registrar |
| 2. Gastos hormiga | Cantidad, total, proyección mensual y anual, los más repetidos, hora del día | `analisis.analisis_hormiga`, Panel |
| 3. Regla 50/30/20 | Agrupa las categorías en necesidades, deseos y ahorro y da un consejo | `analisis.regla_50_30_20`, Panel |
| 4. Gasto inusual | Compara el monto con el de los 5 vecinos del KNN; también avisa si no reconoce ninguna palabra | `MotorIA._revisar_atipico`, Registrar y Panel |

Extras:
- **Explicación**: al registrar, se muestran los 5 vecinos que usó la IA.
- **Confianza baja**: si la categoría ganadora tiene menos del 60% de los votos, la app pide al usuario elegir.
- **Aprendizaje**: cada movimiento guardado o corregido se agrega al "mapa" del KNN sin reentrenar el TF-IDF.
- **Precisión real**: en Historial se ve qué porcentaje de veces el usuario no tuvo que corregir a la IA.
- **Tildes**: el TF-IDF del `.pkl` distingue "cafe" de "café". Sin reentrenar,
  `MotorIA.normalizar_descripcion` cambia cada palabra que el modelo no conoce por su
  versión con (o sin) tilde que sí está en el vocabulario, antes de predecir y aprender.
  La descripción se guarda tal como la escribió el usuario.

## Nota sobre la función `extraer_variables_temporales`

El `.pkl` guarda solo el **nombre** de esta función de su notebook, no su código.
Por eso está reescrita en `modelo_ia.py`. Se reconstruyó revisando los datos
guardados dentro del modelo; devuelve 4 columnas:

- `hora` (0 a 23)
- `dia_semana` (0 = lunes ... 6 = domingo)
- `dia_mes` (1 a 31)
- `es_fin_de_semana` (1 si es viernes, sábado o domingo)

Si en el notebook la función hacía algo distinto, cópienla tal cual en `modelo_ia.py`.

Si vuelven a entrenar el modelo, guárdenlo con la misma versión de scikit-learn
que aparece en `requirements.txt` (1.9.1), o cambien esa versión.
