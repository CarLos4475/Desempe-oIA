# Verificación de la entrega

18 de noviembre de 2026.

## Ejecución

- Se creó un entorno Python 3.12 nuevo, sin reutilizar las bibliotecas del equipo.
- Con solo `requirements.txt`, pasaron las 11 pruebas del dashboard: cinco vistas, controles, descargas y estados de datos incompletos. scikit-learn no estaba instalado en ese entorno mínimo.
- En la actualización de metodología 2.1.0 pasaron las 34 pruebas de la entrega: 12 del análisis, 15 del tablero y su adaptador de datos, y siete de regresión e interpretación de informes.
- Las pruebas de regresión comprueban la separación del objetivo, la referencia del promedio de entrenamiento, la partición reproducible, los R² negativos o no definidos y la exclusión de campos individuales.
- También se comprobó que las conclusiones y los tamaños de partición cambien al recalcular con datos sintéticos, y que se informe cuántos pliegues aportan un R² definido.
- Se reprodujo el arranque con una versión anterior del adaptador todavía importada en memoria. El tablero recarga ese módulo cuando cambia su contrato de resultados o documentos, para recuperar la sesión durante la actualización.
- El notebook se ejecutó de principio a fin sin errores y sus salidas se comprobaron contra los identificadores reales de las fuentes, sin publicarlos.
- El arranque del dashboard no requiere encuestas privadas, PDF originales o entrenamiento de modelos.
- Los datos agregados y los PDF definitivos son los mismos que consulta el tablero.

## Organización y privacidad

- El repositorio incluye dashboard, notebook, análisis, figuras, tablas e informes definitivos.
- La regresión añade `resultados/regresion_metricas.csv` y una figura comparativa, con métricas agregadas de entrenamiento, validación y prueba.
- `requirements.txt` contiene las dependencias del dashboard; análisis y desarrollo tienen archivos separados.
- `.streamlit/config.toml` no fija la aplicación a una dirección local; CORS y XSRF se mantienen activados.
- Se comprobaron los archivos de texto y los dos PDF de la entrega contra los identificadores de las fuentes. No se encontraron números de cuenta reales.
- Las encuestas, PDF originales, secretos, entornos virtuales y notas internas no forman parte del commit de entrega.
- El historial previo del repositorio se conserva: esta organización no reescribe commits anteriores.

## Alcance

Se verificó la ejecución local del tablero con Python 3.12, incluidas las tres pestañas de Modelos y el cambio de métrica de regresión. El tablero consulta resultados calculados; no abre encuestas ni entrena modelos al arrancar.

Los dos informes se generaron de nuevo y se revisaron sus 19 páginas renderizadas: 12 del técnico y siete del de negocio. Se conservaron las portadas originales y el estilo de los documentos. La redacción se revisó con la skill humanizer-es para explicar las métricas sin cambiar cifras, unidades o grado de certeza.

La comprobación cubre el funcionamiento de la aplicación y la coherencia de los archivos. Los resultados siguen siendo exploratorios, con una muestra pequeña y sin calificaciones numéricas verificadas.

## Verificación de la rúbrica

19 de noviembre de 2026. Metodología 2.2.0.

- Se cotejaron las dos fuentes locales con las exportaciones originales. Las huellas de los archivos coinciden con las registradas en el análisis. El notebook muestra la cobertura de las 18 columnas de IA y las nueve seleccionadas de bienestar, con conteos agregados por campo.
- K-Means y KNN ejecutaron `GridSearchCV` y `RandomizedSearchCV`. Las dos búsquedas por modelo se muestran en el notebook, el tablero y `resultados/ajuste_modelos.csv`. La validación de K-Means ajusta escala y centroides dentro de cada pliegue. KNN reserva seis casos para comparar el modelo elegido y la referencia mayoritaria.
- Se ejecutó el notebook completo en un entorno Python 3.12. Los agregados resultantes coincidieron con los del tablero, salvo la hora de ejecución. Se comprobó que las salidas no incluyen números de cuenta.
- Pasaron las 40 pruebas de la entrega. Comprueban la limpieza, el ajuste de ambos modelos, la carga de resultados públicos, las vistas del tablero y las métricas de regresión. El tablero muestra las dos búsquedas en cada pestaña correspondiente y permite descargar ambos informes.
- Se revisaron las 20 páginas renderizadas de los informes definitivos. Las portadas conservan los tres nombres completos y las cifras corresponden a la misma ejecución del análisis.
