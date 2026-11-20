# Uso de inteligencia artificial y desempeño académico

**Proyecto de Sistemas Inteligentes · MAC**

**[Ver tablero interactivo](https://desempe-oia-yxvqtsq3qqremr7yxsxfsg.streamlit.app/)**

[Diapositivas de la exposición](presentacion/index.html) · [Guion en PDF](presentacion/guion.pdf) · [Guía de ensayo de la persona 3](presentacion/ensayo-persona-3.html)

Este proyecto estudia cómo un grupo de estudiantes incorpora herramientas de inteligencia artificial a sus actividades académicas y cómo describe su entorno universitario. Reúne el análisis de dos cuestionarios, un tablero interactivo y los informes técnico y de negocio.

El interés está en conocer para qué se usa la IA, qué herramientas aparecen con mayor frecuencia y qué beneficios o dificultades perciben quienes respondieron. El desempeño académico se aborda desde esas percepciones: las encuestas no incluyen una medición objetiva de calificaciones o aprendizaje.

## Objetivo

Explorar los hábitos de uso de IA y su relación con el contexto académico mediante análisis descriptivo, procesamiento de lenguaje natural y modelos de aprendizaje automático. Los resultados se presentan en gráficas y documentos que permiten revisar tanto los hallazgos como sus límites.

## Datos utilizados

Se trabajó con dos cuestionarios proporcionados para el proyecto:

| Fuente | Formato | Respuestas | Contenido |
| --- | --- | ---: | --- |
| Desempeño académico por el uso de IA | Excel | 24 | Herramientas, tiempo de uso, propósitos y percepciones sobre el estudio |
| Entorno Universitario y Bienestar | CSV | 19 | Traslado, ambiente en casa, sueño y experiencias de bienestar |

Los 19 registros de bienestar se emparejaron con su respuesta sobre IA. Las cinco personas sin segunda encuesta conservaron esos campos como datos ausentes. Los archivos originales contienen identificadores y se mantienen fuera de la entrega pública; el tablero utiliza resultados agregados.

## Herramientas y técnicas

| Herramienta | Uso en el proyecto |
| --- | --- |
| Python y Jupyter Notebook | Desarrollo y presentación del análisis |
| pandas y NumPy | Limpieza, transformación y resumen de los datos |
| `re`, `unicodedata` y `difflib` | Expresiones regulares, normalización de texto y similitud de nombres de herramientas |
| scikit-learn | K-Means, KNN, búsquedas de hiperparámetros, TF-IDF, imputación, escalamiento y PCA |
| SciPy | Correlación de Spearman y análisis estadístico |
| Matplotlib y WordCloud | Figuras del estudio y exploración de términos |
| Streamlit y Altair | Tablero interactivo y visualización de resultados |
| ReportLab y pypdf | Elaboración de los informes, conservando las portadas originales |
| unittest y Streamlit AppTest | Comprobación del análisis y del tablero |

## Desarrollo del análisis

1. **Limpieza en Python.** El flujo parte de las exportaciones originales. Trata los 18 campos de IA y las variables de bienestar que incorpora al análisis. Aplica validación de tipos y formatos, expresiones regulares, unificación de unidades y similitud de cadenas para variantes de herramientas. El notebook muestra las reglas y los conteos por campo.
2. **EDA y KPIs.** Se revisan distribuciones, frecuencias, medianas y correlaciones. Los porcentajes indican qué grupo de respuestas se usó. TF-IDF y la polaridad léxica resumen el lenguaje de las encuestas.
3. **Aprendizaje no supervisado.** K-Means explora agrupaciones con los casos que respondieron ambas encuestas. `GridSearchCV` y `RandomizedSearchCV` comparan configuraciones mediante la silueta en validación. Las agrupaciones se describen como patrones exploratorios de esta muestra.
4. **Aprendizaje supervisado.** KNN intenta distinguir el uso mixto del exclusivo. Se prueban `GridSearchCV` y `RandomizedSearchCV` con F1 en los pliegues del entrenamiento. El modelo ajustado se evalúa en los seis casos reservados junto a la referencia mayoritaria. La comparación de clasificadores con parámetros fijos se conserva como exploración aparte.
5. **Regresión complementaria.** Se evalúa si el semestre de inicio y la cantidad de herramientas ayudan a estimar las horas diarias declaradas. Se usan R², MAE y RMSE y se compara contra el promedio de entrenamiento.
6. **Tablero analítico.** Streamlit reúne los KPIs, las gráficas, los resultados de los modelos y ambos informes.

## Principales resultados

| Indicador | Resultado |
| --- | ---: |
| Respuestas sobre uso de IA | 24 |
| Respuestas sobre entorno y bienestar | 19 |
| Tiempo diario de uso de IA, mediana | 1.5 horas |
| Uso mixto: aprender y agilizar tareas | 13 de 24 (54.2 %) |
| Uso de más de una herramienta | 13 de 24 (54.2 %) |
| Herramienta con más menciones | Gemini: 15 de 24 |
| Tiempo de traslado, mediana | 60 minutos |

Las herramientas admiten varias menciones por persona, por lo que sus porcentajes no deben sumarse como categorías excluyentes.

La relación entre el tiempo de traslado y las horas de IA fue débil en esta muestra (Spearman ρ = 0.137, p = 0.575, n = 19).

- **K-Means.** Las dos búsquedas eligieron cuatro grupos. La silueta media en validación fue 0.196. En la muestra completa quedaron grupos de 12, 5, 1 y 1 personas, con silueta de 0.110. La separación es baja y dos grupos son casos aislados.
- **KNN.** La mejor configuración obtuvo F1 medio de 0.627 en validación, frente a 0.713 de la referencia mayoritaria. En la prueba, KNN acertó cinco de seis casos y la referencia cuatro. Una diferencia de un acierto en una prueba tan pequeña requiere confirmación con más datos.

Las configuraciones elegidas y sus resultados se pueden consultar en el notebook, el tablero y el [CSV de búsquedas](resultados/ajuste_modelos.csv).

### Regresión: ¿podemos estimar las horas de IA?

Este ejercicio estudia intensidad de uso. El objetivo son las horas declaradas en la encuesta, no las calificaciones. Ambos modelos se evaluaron con los mismos seis casos reservados:

| Modelo | R² de prueba | MAE (horas) | RMSE (horas) |
| --- | ---: | ---: | ---: |
| Regresión lineal | −0.245 | 0.808 | 1.039 |
| Referencia: promedio de entrenamiento | −0.064 | 0.634 | 0.961 |

La regresión se desvió unos 48 minutos en promedio, frente a 38 de la referencia. En esta prueba, el semestre de inicio y la cantidad de herramientas no redujeron el error medio. La validación también mostró mucha variación entre pliegues pequeños, lo que limita la confianza en una predicción futura.

R² puede ser negativo: significa que el modelo tuvo más error cuadrático que usar la media del conjunto evaluado. No es un porcentaje de precisión. La referencia de la tabla usa la media de entrenamiento, por eso también puede tener R² negativo en prueba. MAE expresa el error absoluto medio y RMSE da más peso a los errores grandes; ambas métricas se expresan en horas.

![Menciones de herramientas de inteligencia artificial](resultados/figuras/herramientas.png)

## Tablero interactivo

El tablero organiza la consulta en cinco apartados:

- **Panorama:** tamaño de la muestra, indicadores generales y modalidades de uso.
- **Uso de IA:** herramientas, inicio de uso y percepciones sobre el reemplazo profesional.
- **Entorno y bienestar:** traslados, lenguaje de las respuestas y asociaciones exploratorias.
- **Modelos:** clasificación y agrupación con sus búsquedas de parámetros, además de la regresión complementaria con R².
- **Documentación:** consulta y descarga de los informes del proyecto.

Los controles permiten explorar los agregados disponibles. Los porcentajes de herramientas conservan como denominador las 24 respuestas; seleccionar una herramienta no reconstruye cruces individuales con bienestar.

## Contenido de la entrega

| Archivo o carpeta | Contenido |
| --- | --- |
| **Código Python** | [Notebook descargable](Analisis_IA_Desempeno_MAC_Cuestionarios.ipynb), [limpieza por campo](limpieza_encuestas.py), [análisis y modelos](analisis.py), [figuras](visualizaciones.py) y [generación de informes](reportes.py) |
| **Dependencias versionadas** | [Análisis y reportes](requirements-analysis.txt), [tablero](requirements.txt) y [entorno completo con Jupyter y pruebas](requirements-dev.txt) |
| **Tablero analítico** | [Consulta en Streamlit](https://desempe-oia-yxvqtsq3qqremr7yxsxfsg.streamlit.app/), [código de la aplicación](dashboard.py) y [lectura de agregados](dashboard_datos.py) |
| **Documento técnico** | [Consultar o descargar el PDF](docs/DOCUMENTACION_TECNICA.pdf) |
| **Documento de negocio** | [Consultar o descargar el PDF](docs/DOCUMENTACION_NEGOCIO.pdf) |
| **Resultados y evidencia** | [Tablas y figuras](resultados/), [metodología](docs/METODOLOGIA.md), [guía de interpretación](docs/INTERPRETACION.md) y [verificación](tests/VERIFICACION.md) |
| **Exposición** | [Diapositivas, guion y guía de práctica](presentacion/) |

Los dos PDF incluyen los nombres completos del equipo en sus portadas. El notebook se incluye como archivo `.ipynb` con salidas visibles. Usa las encuestas privadas para recalcular y consulta los mismos agregados que el tablero y los informes en [`resultados/resumen.json`](resultados/resumen.json).

## Alcance y conclusiones

La muestra permite describir experiencias del grupo encuestado. No representa a toda la carrera ni permite atribuir cambios en el rendimiento al uso de IA. Las respuestas ambiguas se conservan como tales, y las agrupaciones se interpretan como una exploración, sin diagnósticos ni perfiles individuales.

El proyecto muestra distintas formas de integrar la IA al estudio, con un uso frecuente que combina apoyo para aprender y ahorro de tiempo. Las evaluaciones predictivas también ayudan a reconocer qué no explican bien las variables disponibles. Para estudiar el efecto sobre el desempeño harían falta más participantes, mediciones académicas objetivas y un seguimiento a lo largo del tiempo.
