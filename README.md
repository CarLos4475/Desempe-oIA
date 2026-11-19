# Uso de inteligencia artificial y desempeño académico

**Proyecto de Sistemas Inteligentes · MAC**

**[Ver tablero interactivo](https://desempe-oia-yxvqtsq3qqremr7yxsxfsg.streamlit.app/)**

[Diapositivas de la exposición](presentacion/index.html) · [Guion en PDF](presentacion/guion.pdf)

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
| scikit-learn | TF-IDF, imputación, escalamiento, PCA, clasificación y agrupamiento |
| SciPy | Correlación de Spearman y análisis estadístico |
| Matplotlib y WordCloud | Figuras del estudio y exploración de términos |
| Streamlit y Altair | Tablero interactivo y visualización de resultados |
| ReportLab y pypdf | Elaboración de los informes, conservando las portadas originales |
| unittest y Streamlit AppTest | Comprobación del análisis y del tablero |

Se compararon regresión logística, SVM, Random Forest y KNN con una referencia que predice siempre la clase mayoritaria. Un segundo ejercicio utiliza regresión lineal para estimar horas de uso de IA y la compara con el promedio de entrenamiento. También se exploraron agrupaciones mediante K-Means y clustering jerárquico.

## Desarrollo del análisis

1. **Preparación de las fuentes.** Validación de columnas y registros únicos, cruce de cuestionarios y normalización de horas, traslados y nombres de herramientas.
2. **Análisis descriptivo.** Revisión de frecuencias, porcentajes, medianas y distribuciones, manteniendo la base de cada encuesta.
3. **Análisis de texto.** Extracción de términos con TF-IDF y cálculo de polaridad léxica con tratamiento de negaciones. Este indicador describe el lenguaje y no constituye una escala clínica o académica.
4. **Clasificación supervisada.** Distinción entre uso declarado mixto y uso exclusivo como guía o atajo. La pregunta que define la etiqueta se excluyó de los predictores. Se usaron 16 casos de entrenamiento, validación cruzada de cinco pliegues y seis casos reservados para prueba.
5. **Regresión del tiempo de uso.** Estimación de horas diarias de IA a partir del semestre de inicio y la cantidad de herramientas. Se usaron 18 casos de entrenamiento, cinco pliegues de validación y seis casos reservados para prueba. La evaluación incluye R², MAE y RMSE.
6. **Exploración del entorno.** Correlaciones y agrupamiento con las 19 observaciones reales de bienestar, sin completar encuestas faltantes con datos inventados.
7. **Presentación.** Integración de los resultados en el notebook, las figuras, el tablero y los dos informes.

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

No se observó una relación clara entre el tiempo de traslado y las horas de IA en esta muestra (Spearman: rho = 0.137; p = 0.575; n = 19). En la clasificación, la referencia mayoritaria obtuvo un F1 medio de 0.713 en validación, por encima de la regresión logística (0.627). El ejercicio no ofrece evidencia suficiente para realizar predicciones individuales.

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
- **Modelos:** clasificación, regresión con R² y exploración de agrupaciones, cada una en su propia pestaña.
- **Documentación:** consulta y descarga de los informes del proyecto.

Los controles permiten explorar los agregados disponibles. Los porcentajes de herramientas conservan como denominador las 24 respuestas; seleccionar una herramienta no reconstruye cruces individuales con bienestar.

## Contenido de la entrega

| Archivo o carpeta | Contenido |
| --- | --- |
| [Notebook del análisis](Analisis_IA_Desempeno_MAC_Cuestionarios.ipynb) | Desarrollo del estudio con resultados y figuras |
| [analisis.py](analisis.py) | Preparación de datos, análisis de texto y evaluación de modelos |
| [dashboard.py](dashboard.py) y [dashboard_datos.py](dashboard_datos.py) | Aplicación y lectura de resultados agregados |
| [resultados/](resultados/) | Resumen JSON, tablas CSV y gráficas |
| [visualizaciones.py](visualizaciones.py) | Generación de figuras |
| [reportes.py](reportes.py) | Generación de los informes PDF |
| [verificar_notebook.py](verificar_notebook.py) | Ejecución y comprobación del notebook |
| [tests/](tests/) | Pruebas del análisis y del tablero |
| Archivos `requirements*.txt` | Dependencias de la aplicación, el análisis y la validación |

La documentación del proyecto se encuentra en:

- [Informe técnico](docs/DOCUMENTACION_TECNICA.pdf).
- [Informe de negocio](docs/DOCUMENTACION_NEGOCIO.pdf).
- [Metodología y alcance](docs/METODOLOGIA.md).
- [Guía para interpretar los resultados](docs/INTERPRETACION.md).
- [Verificación de la entrega](tests/VERIFICACION.md).

Los dos PDF son los informes definitivos del proyecto y conservan las portadas y el estilo de los documentos de referencia. Toda la documentación se encuentra directamente en [docs/](docs/), con un índice para consultarla. El notebook, el tablero y los informes comparten los resultados de `resultados/resumen.json`.

## Alcance y conclusiones

La muestra permite describir experiencias del grupo encuestado. No representa a toda la carrera ni permite atribuir cambios en el rendimiento al uso de IA. Las respuestas ambiguas se conservan como tales, y las agrupaciones se interpretan como una exploración, sin diagnósticos ni perfiles individuales.

El proyecto muestra distintas formas de integrar la IA al estudio, con un uso frecuente que combina apoyo para aprender y ahorro de tiempo. Las evaluaciones predictivas también ayudan a reconocer qué no explican bien las variables disponibles. Para estudiar el efecto sobre el desempeño harían falta más participantes, mediciones académicas objetivas y un seguimiento a lo largo del tiempo.
