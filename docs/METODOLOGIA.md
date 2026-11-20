# Metodología y alcance

El análisis reúne 24 respuestas sobre uso de IA y 19 sobre entorno universitario. Las claves se usan en memoria para validar y emparejar los registros de uno a uno. Los archivos públicos contienen solo resultados agregados.

## Limpieza en Python

Python lee el XLSX y el CSV directamente. La preparación valida los encabezados y el orden de las preguntas, convierte la marca temporal, normaliza las claves y comprueba que la unión sea de uno a uno. Los archivos originales se conservan byte por byte. Las huellas SHA-256 registradas en `resultados/resumen.json` ayudan a identificar las fuentes de esta ejecución.

Se aplica un tratamiento a los 18 campos del formulario de IA, incluida la pregunta opcional de otros usos. La limpieza de bienestar cubre la clave de cruce y las variables incorporadas al estudio. El notebook enumera las columnas cubiertas, las que quedan fuera del alcance y, por cada campo, la regla aplicada y los conteos de ausencias y modificaciones.

Las expresiones regulares permiten extraer unidades y variantes como «Chat GPT». Después de los patrones y alias se aplica similitud de cadenas con un criterio conservador para los nombres de herramientas. Un alias de una herramienta ya reconocida no aumenta su frecuencia. Las duraciones en rangos se aproximan y se convierten a horas o minutos según corresponda. El texto abierto conserva su contenido y una respuesta en blanco permanece como ausente.

Las cinco personas sin encuesta de bienestar conservan esos datos como faltantes. El EDA, las asociaciones con el entorno y el agrupamiento usan las 19 observaciones disponibles de bienestar. No se exportan claves, marcas temporales ni respuestas abiertas.

## Análisis exploratorio e indicadores

Se describen distribuciones, medianas, frecuencias, valores extremos y correlaciones de Spearman. El tiempo típico de IA y de traslado se resume con medianas y sus respectivos tamaños de muestra. La proporción de uso mixto incluye en el denominador a las 24 respuestas del formulario de IA. La diversidad de herramientas cuenta cuántas personas mencionaron al menos dos. Las menciones individuales de herramientas son multirrespuesta. La documentación de negocio explica el significado de cada indicador y los posibles usos de seguimiento.

## Análisis del lenguaje

TF-IDF resume términos destacados mediante unigramas y bigramas, con hasta 30 características. La polaridad se calcula por pregunta con un lexicón que contempla negaciones y expresiones de alivio. Después se promedian las preguntas respondidas.

Este indicador describe señales del lenguaje. No tiene validación como escala académica o clínica. Un cero puede aparecer porque no hubo palabras reconocidas, especialmente en respuestas de frecuencia, y no demuestra neutralidad emocional. La ironía, la ambigüedad y las negaciones lejanas siguen siendo límites del procedimiento.

## Clasificación de modalidad

La etiqueta distingue uso mixto de uso exclusivo como guía o atajo. Se excluyen las dos respuestas ambiguas o no clasificables, y la pregunta que define la etiqueta no entra en los predictores.

Los 22 casos etiquetables se dividen de forma estratificada en 16 para entrenamiento y seis para prueba, con semilla 42. La validación cruzada de cinco pliegues se realiza solo sobre entrenamiento. En cada pliegue se vuelven a ajustar escala, imputación KNN, TF-IDF y PCA, evitando aprender de los casos que se van a evaluar.

El ajuste principal utiliza `KNeighborsClassifier`. `GridSearchCV` recorre una cuadrícula de configuraciones y `RandomizedSearchCV` revisa una selección reproducible del espacio de búsqueda. Ambas usan los mismos pliegues estratificados de entrenamiento y seleccionan por F1 medio. El notebook informa cuántas configuraciones se evaluaron, cuáles quedaron arriba y cómo cambiaron sus resultados entre pliegues. La configuración de KNN seleccionada se evalúa en los casos reservados junto a la referencia mayoritaria.

En una comparación exploratoria aparte se evalúan regresión logística, SVM, Random Forest y un KNN de parámetros fijos. Entre ellos se elige un candidato por F1 medio de validación, con desempate por accuracy y menor dispersión. El KNN ajustado de la actividad principal tiene su propio resultado. Los casos de prueba se consultan después de esas decisiones.

Se reportan accuracy, precisión, recall, F1 y matriz de confusión. Con seis casos de prueba, un acierto cambia accuracy en 16.7 puntos porcentuales. La tarea evalúa categorías declaradas de uso, sin medir aprendizaje efectivo.

## Regresión complementaria de horas de uso

El objetivo numérico es `horas_ia_dia`. Los predictores son `semestre_inicio` y `total_herramientas`; el objetivo no se utiliza como entrada. Se conservan casos completos con valores finitos y horas no negativas. En esta ejecución se utilizaron los 24 casos y no hubo exclusiones.

Se fija una partición 75/25 con semilla 42: 18 casos de entrenamiento y seis de prueba. La regresión lineal con escalamiento se compara con `DummyRegressor(strategy='mean')`, que predice el promedio del conjunto con el que se entrena. No se buscan hiperparámetros ni se seleccionan modelos o particiones por su resultado de prueba.

Sobre los 18 casos de entrenamiento se aplica `KFold` de cinco pliegues, mezclados con semilla 42. Cada pliegue vuelve a ajustar el modelo y el escalamiento con su parte de entrenamiento. Luego ambos modelos se ajustan sobre los 18 casos y se evalúan en los mismos seis de prueba. Esta partición es propia de la regresión y no tiene por qué coincidir con la clasificación.

Se calculan R², MAE y RMSE en entrenamiento, por pliegue y en prueba. El resumen de CV contiene la media de los R² definidos, su desviación estándar, el número de pliegues válidos y las medias de MAE y RMSE. No es un R² obtenido al reunir todas las predicciones. Un pliegue con horas constantes conserva R² nulo; se mantienen sus errores en horas. Si no hay suficientes casos o variación para entrenar, el ejercicio se informa como insuficiente.

R² puede ser negativo y no se recorta. Su referencia matemática usa la media del conjunto evaluado, mientras que el modelo de referencia usa la media de entrenamiento. MAE y RMSE se expresan en horas. Las tablas públicas y las figuras muestran métricas, sin predicciones individuales. La regresión evalúa intensidad declarada de uso, no calificaciones ni efectos de la IA sobre el desempeño.

## Asociaciones y agrupación

Se exploran correlaciones de Spearman sin ajuste por comparaciones múltiples. Una asociación no prueba causalidad, y un valor p alto tampoco prueba que la relación no exista.

K-Means usa seis variables estandarizadas de los 19 registros con entorno observado. `GridSearchCV` y `RandomizedSearchCV` buscan configuraciones con silueta de validación. Cada pliegue entrena el escalador y los centroides, asigna las observaciones de validación a esos centroides y calcula la silueta donde las etiquetas lo permiten. Un pliegue sin una silueta definida aporta una penalización de −1 para la búsqueda. Se informa cuántos pliegues permitieron calcularla para distinguir ese caso de una silueta medida.

La silueta de la solución final se calcula en la muestra completa para describirla. El recorrido de k de 2 a 5 en esa misma muestra y el agrupamiento jerárquico son comparaciones descriptivas. PCA ayuda a representar parte de la variación. El tamaño desigual de los grupos y la muestra pequeña limitan cualquier interpretación como un perfil estable del alumnado. Se omiten perfiles si un grupo o su complemento tienen menos de tres personas.

## Reproducibilidad y lectura

`resultados/resumen.json` registra la versión de metodología, las versiones de bibliotecas y las huellas de las fuentes. El notebook, las figuras, el tablero y los PDF usan el mismo análisis. Las encuestas se necesitan para recalcular y las portadas originales para regenerar los informes. Los archivos de referencia quedan fuera de Git.

La [guía de interpretación](INTERPRETACION.md) explica las métricas con los resultados de esta ejecución. Para consultar las definiciones técnicas, véase la documentación de scikit-learn 1.6.1 sobre [GridSearchCV](https://scikit-learn.org/1.6/modules/generated/sklearn.model_selection.GridSearchCV.html), [RandomizedSearchCV](https://scikit-learn.org/1.6/modules/generated/sklearn.model_selection.RandomizedSearchCV.html) y [evaluación de modelos](https://scikit-learn.org/1.6/modules/model_evaluation.html).
