# Cómo interpretar los resultados

Las encuestas reúnen experiencias de 24 personas sobre uso de IA. De ellas, 19 también respondieron sobre entorno y bienestar. Cada cifra describe a quienes contestaron; la muestra no permite extender las conclusiones a toda la carrera.

## Frecuencias, porcentajes y tiempo de uso

La mediana de 1.5 horas diarias ubica el centro de las respuestas ordenadas. No indica que cada persona use IA ese tiempo ni establece un límite saludable. Las respuestas sobre duración son aproximaciones declaradas, en algunos casos convertidas desde minutos o rangos.

Gemini tiene 15 menciones entre las 24 respuestas, y 13 personas mencionan al menos dos herramientas. Como una misma persona puede aparecer en varias barras, los porcentajes de herramientas no se suman como si fueran grupos distintos. Los filtros del tablero mantienen la base de 24.

El 54.2 % de uso híbrido describe respuestas que combinan aprender con agilizar tareas. La categoría expresa el propósito declarado, sin comprobar por sí sola la calidad del aprendizaje.

## Qué se prueba al ajustar un modelo

`GridSearchCV` recorre todas las combinaciones de una lista. `RandomizedSearchCV` toma una selección del espacio que definimos. Es parecido a probar recetas con distintas cantidades de un ingrediente: podemos seguir todas las combinaciones de una lista corta o elegir algunas de una lista más larga. En el notebook aparecen las configuraciones revisadas, los parámetros elegidos y sus puntajes de validación.

En K-Means se compara la separación de grupos de los casos apartados en cada pliegue. En KNN se compara qué tan bien se reconoció la modalidad mixta. Los dos puntajes responden a tareas distintas.

## Qué tan bien se clasifica la modalidad de uso

La clasificación intenta distinguir uso mixto de uso exclusivo como guía o atajo. La clase positiva es la modalidad mixta. La pregunta que define la categoría se excluye de los predictores.

- **Accuracy** es la proporción total de aciertos.
- **Precisión** indica cuántos casos predichos como mixtos lo eran realmente según la etiqueta.
- **Recall** indica cuántos casos mixtos logra recuperar el modelo.
- **F1** combina precisión y recall para valorar ambas en una sola cifra.

KNN clasifica cada respuesta según cómo se etiquetaron sus casos de entrenamiento más cercanos. Las dos búsquedas ayudan a elegir esa configuración sin usar los seis casos reservados. Para leer la prueba, se compara KNN ajustado con la referencia que siempre elige la modalidad más frecuente. Con seis casos, un acierto cambia accuracy en 16.7 puntos porcentuales. El informe técnico distingue este resultado de la comparación aparte entre clasificadores de parámetros fijos.

En validación, la cuadrícula obtuvo F1 medio de 0.627 y la búsqueda aleatoria 0.560. La referencia mayoritaria obtuvo 0.713. En los seis casos reservados, el KNN elegido acertó cinco y obtuvo F1 de 0.889. La referencia acertó cuatro y obtuvo F1 de 0.800. La ventaja en prueba equivale a un acierto y queda pendiente comprobar si se repite en una muestra mayor.

## Regresión complementaria de horas de uso

La regresión lineal responde otra pregunta: si el semestre de inicio y la cantidad de herramientas ayudan a estimar las horas diarias de IA. Se evalúa con 24 casos completos, distribuidos en 18 de entrenamiento y seis de prueba. Esta partición es independiente de la clasificación.

**R² = 1 − SSE/SST.** SSE es la suma de los errores cuadrados y SST mide la variación de las horas respecto de su media en el conjunto evaluado.

| R² | Lectura |
| --- | --- |
| 1 | Las predicciones coinciden con todos los valores evaluados. |
| 0 | El error cuadrático equivale a predecir la media de ese conjunto. |
| Menor que 0 | El modelo tiene más error cuadrático que esa referencia matemática. |
| No definido | Las horas evaluadas son constantes y no hay variación para calcular la comparación. |

El R² de prueba de la regresión fue −0.245. No significa “−24.5 % de precisión” ni demuestra que la IA empeore las calificaciones. Indica que las estimaciones del modelo resultaron deficientes en esos seis casos.

La referencia del proyecto predice la **media de entrenamiento**, calculada sin conocer la prueba. Esa media puede diferir de la media de los seis casos evaluados, por lo que su R² de prueba también puede ser negativo: en esta ejecución fue −0.064.

**MAE** es el promedio de las diferencias absolutas entre predicción y respuesta. El modelo tuvo MAE de 0.808 horas, unos 48 minutos, frente a 0.634 horas, unos 38 minutos, de la referencia. Son errores medios y no márgenes garantizados para cada persona.

**RMSE** eleva al cuadrado los errores antes de promediarlos y luego toma la raíz. Se expresa en horas y da más peso a las equivocaciones grandes. Fue 1.039 horas para la regresión y 0.961 para la referencia.

Los dos predictores no mejoraron esas métricas de prueba frente al promedio. Hace falta una muestra mayor para saber si esto se mantiene. No se cambiaron modelos, parámetros ni semillas buscando un R² positivo.

## Qué aporta la validación cruzada

Para clasificación y regresión, cada pliegue aparta una parte del conjunto de entrenamiento para validar y usa el resto para aprender las transformaciones del modelo. Los casos reservados para la prueba final quedan fuera de ese proceso.

En regresión, cada pliegue evalúa tres o cuatro respuestas. Si las horas de un pliegue son muy parecidas, incluso un error pequeño puede producir un R² muy negativo. El promedio de R² por pliegue no equivale a calcular un único R² sobre todas las predicciones reunidas. Los pliegues con horas constantes conservan R² nulo y se informa cuántos valores definidos entran al promedio.

La desviación estándar entre pliegues muestra cuánto cambiaron los resultados. No es un intervalo de confianza ni corrige la falta de datos.

## Correlaciones, lenguaje y grupos

La correlación de Spearman entre traslado y horas de IA fue 0.137, con p = 0.575 y 19 pares. En esta muestra no aparece una asociación monotónica clara. Un valor p alto tampoco prueba que la relación no exista. Las correlaciones adicionales son exploratorias y no se ajustaron por comparaciones múltiples.

La polaridad resume palabras y expresiones reconocidas en las respuestas. Un cero puede indicar equilibrio entre señales o falta de vocabulario coincidente. No debe interpretarse como bienestar neutral. El indicador no es una escala clínica ni una medición del aprendizaje.

K-Means agrupó los 19 casos con entorno observado. La silueta ayuda a leer qué tan juntos quedan los casos de un grupo y qué tan separados quedan de los demás. Si un pliegue de búsqueda no produce etiquetas suficientes para calcularla, la comparación usa una penalización de −1 y lo registra aparte. La silueta del ajuste final se calcula en la muestra completa y describe esa agrupación. Los tamaños de grupo ayudan a ver cuándo pocos casos explican buena parte de la separación. Se omiten descripciones de grupos o complementos menores de tres personas para proteger las respuestas individuales.

Las dos búsquedas coincidieron en cuatro grupos con una silueta media de 0.196 en validación y tres pliegues válidos. Tras el ajuste con los 19 casos quedaron grupos de 12, 5, 1 y 1 personas. La silueta de ese ajuste fue 0.110. La cercanía a cero y los casos aislados indican que los grupos requieren más evidencia antes de interpretarlos como perfiles del alumnado.

## Qué conclusión sí puede sostenerse

El estudio describe hábitos y percepciones, y muestra cómo se comportan varias técnicas con pocos datos. El tamaño de la muestra limita cuánto podemos esperar que se repitan las comparaciones de clasificación, regresión y agrupación. Para estudiar efectos sobre el desempeño académico se necesitan calificaciones numéricas independientes, más participantes y seguimiento en el tiempo.
