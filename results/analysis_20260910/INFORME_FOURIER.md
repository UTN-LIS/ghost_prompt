# Análisis de Fourier de las métricas por posición de generación

## Alcance

Se analizó `aligned_positions.csv`, con 1.649 ventanas de lookahead de 20 problemas y posiciones de generación entre 2 y 244. Las métricas disponibles son persistencia alineada, divergencia semántica alineada y score semántico alineado.

En estos datos, “posición” significa índice de decisión dentro de la generación. No es tiempo físico ni una señal muestreada regularmente: hay posiciones sin observaciones y distinta cantidad de problemas por posición. Por eso el análisis espectral es exploratorio y describe periodicidad o repetición a lo largo del eje de generación; no prueba un mecanismo causal del modelo.

## Método

Para cada métrica se calculó la media por posición. Las posiciones sin media se interpolaron linealmente únicamente para poder aplicar la FFT sobre una grilla regular; el número de observaciones originales se conserva en `fourier_position_spectrum.csv`. Se quitó una tendencia lineal antes de la transformada y se usó potencia ( |FFT|^2 ). Los picos se expresan como ciclos por posición y como período aproximado en posiciones.

La interpolación y el detrending son decisiones analíticas, no datos observados. Cerca de los extremos la señal es especialmente sensible a ellas. No se asignaron ceros a posiciones faltantes.

## Resultados

Los resultados reproducibles están en `fourier_results.json` y `fourier_position_spectrum.csv`. El script es `fourier_analysis.py`.

### Interpretación correcta

- Un pico con período, por ejemplo, 20 posiciones indicaría una oscilación promedio cada aproximadamente 20 decisiones de generación.
- Un pico de período muy largo puede ser simplemente el remanente de una tendencia o de la cobertura desigual de las tareas.
- Un pico compartido por persistencia, divergencia y score es más compatible con una estructura común del protocolo; no implica que el modelo tenga un “ritmo” interno.
- Para afirmar significancia habría que comparar cada pico con un null que preserve la autocorrelación, por ejemplo bloques o surrogates, y corregir por los múltiples bins espectrales.

## Limitaciones principales

1. Solo hay 20 tareas y muchas posiciones tienen pocas observaciones.
2. Las métricas provienen de ventanas seleccionadas/registradas, no de todas las generaciones posibles.
3. Las posiciones no están igualmente observadas; la FFT requiere regularización mediante interpolación.
4. No hay series completas token a token por rama en los CSV actuales. Para un análisis más fuerte habría que exportar, para cada tarea y rama, la secuencia completa de entropía, margen, token rank y resultado final.
5. La señal puede reflejar estructura del código —inicios de bloques, líneas, indentación— y no una periodicidad estadística general del LLM.

## Qué puede aportar a tu investigación

El análisis sirve para decidir si los errores se concentran en bandas de posiciones o si existen “zonas” repetitivas donde conviene activar el branching preventivo. Si los picos desaparecen al estratificar por tarea o por tipo de token, no conviene usar una regla global por posición. Si persisten en varias tareas/modelos, se puede incorporar la fase/posición como feature barata del predictor de valor contrafactual.

La prueba más relevante para tu hipótesis sería comparar la tasa de decisiones recuperables en posiciones de alta potencia espectral contra posiciones sin esa señal, manteniendo fijo el presupuesto computacional y validando en tareas nuevas.
