# Análisis estadístico como serie temporal

## Resumen

Se trató la posición dentro de la generación como un índice temporal discreto y se agregaron las 1.649 ventanas por posición. El intervalo observado va de la posición 2 a la 244: 243 posiciones posibles, de las cuales cada métrica tiene observaciones en el mismo conjunto de posiciones registradas y faltantes en las restantes. Las posiciones ausentes se interpolaron linealmente solo para obtener una grilla regular para autocorrelación, AR(1) y Fourier; no se transformaron en observaciones originales.

El resultado más importante es que hay **dependencia local débil/moderada alrededor de lag 2** y un pico espectral común cercano a **27 posiciones**, pero la evidencia no permite afirmar estacionalidad estable. La cobertura es irregular, solo hay 20 tareas y el eje representa posición de decodificación, no tiempo físico. El patrón debe usarse como señal exploratoria, no como regla validada de branching.

## Datos y controles

| Elemento | Resultado |
|---|---:|
| Filas de lookahead | 1.649 |
| Tareas | 20 |
| Posición mínima–máxima | 2–244 |
| Posiciones posibles | 243 |
| Métricas | persistencia alineada, divergencia alineada, score semántico alineado |
| Unidad real | ventana por tarea y posición |

La unidad original no es una observación temporal independiente: ventanas de la misma tarea comparten contexto y pueden estar correlacionadas. Por eso los resultados se interpretan como una señal agregada descriptiva, no como inferencia poblacional sobre tokens independientes.

## Método estadístico

Para cada métrica (y_t):

1. Se calculó la media, desviación estándar y cantidad de ventanas por posición.
2. Se conservó la cobertura original y se interpolaron medias faltantes únicamente para disponer de una serie equiespaciada.
3. Se ajustó la tendencia lineal (y_t=\beta_0+\beta_1t+e_t).
4. Se calcularon autocorrelaciones de los residuos para lags 1–10.
5. Se calculó el estadístico Ljung–Box descriptivo para 10 lags.
6. Se ajustó un AR(1) por mínimos cuadrados sobre los residuos.
7. Se obtuvo el espectro de potencia de Fourier de los residuos y se ordenaron sus picos.
8. Se compararon medias de la primera/segunda mitad y de cuatro cuartiles como diagnóstico de no estacionariedad.

Los resultados numéricos completos están en `time_series_results.json`; el script reproducible es `time_series_analysis.py`.

## Resultados clave

### Dependencia y autocorrelación

La autocorrelación de lag 1 es cercana a cero o negativa, mientras que el lag 2 es positivo y ronda 0,19–0,27 según la métrica. Esto sugiere que algunos valores separados por dos posiciones se parecen más que los adyacentes, pero no es evidencia suficiente de una dinámica AR simple. El estadístico Ljung–Box de 10 lags se reporta en el JSON; no se presenta un p-valor chi-cuadrado porque la interpolación y la dependencia por tarea violan la aproximación iid habitual.

El AR(1) estimado no debe interpretarse como un modelo generativo del LLM: el índice tiene huecos y las ventanas provienen de tareas distintas. Sirve como resumen de persistencia local de la señal agregada.

### Tendencias

La persistencia alineada presenta una pendiente negativa pequeña por posición. La divergencia tiene una pendiente prácticamente nula y el score semántico una pendiente positiva muy pequeña. La diferencia entre mitades y los promedios por cuartil están en `time_series_results.json`; su lectura debe considerar que las posiciones tardías tienen menor y distinta cobertura.

Los intervalos de pendiente incluidos en el JSON son intervalos normales de OLS, no intervalos robustos a la dependencia temporal. Por eso no se usan para declarar significancia; un análisis confirmatorio debería usar errores HAC o bootstrap por tarea.

### Espectro

En las tres señales aparece un pico cercano a período 27 posiciones. También aparecen picos de período 2–2,5 posiciones, de frecuencia alta. El primero es más interesante como posible estructura de bloques o zonas de decisión; el segundo es compatible con alternancia local, discretización de tokens o ruido de la interpolación.

No se puede llamar “estacionalidad” a esos picos sin un contraste nulo apropiado. La prueba siguiente debe preservar la estructura por tarea y generar series nulas mediante permutaciones por bloques o desplazamientos circulares dentro de cada tarea, no barajar todos los puntos globalmente.

## Implicación para el branching preventivo

La posición puede incorporarse como feature auxiliar, especialmente si el patrón de aproximadamente 27 posiciones se replica en modelos y benchmarks nuevos. No conviene disparar branching simplemente cada 27 posiciones. La regla debe combinar:

`posición/fase + entropía alta + margen bajo + evento estructural de código`.

El test principal sería comparar la tasa de recuperaciones preventivas en posiciones cercanas a los picos contra posiciones de control, a igual presupuesto de tokens/FLOPs y con tareas nuevas. Si el pico desaparece al estratificar por tarea, lenguaje o tipo de token, era composición de datos y no una señal generalizable.

## Comparación espectral PASS vs. FAIL en ramas

Se repitió la FFT usando solo las 255 ramas completas etiquetadas: 29 PASS y 226 FAIL. El resultado no debe interpretarse como una comparación temporal confirmatoria, porque hay muy pocas ramas PASS y muchas posiciones no tienen una observación de cada clase.

La principal diferencia es de nivel, no de periodicidad: las ramas PASS tienen entropía media 0,676 frente a 0,258 en FAIL, y margen medio 0,577 frente a 0,822. Al calcular el espectro de las medias por posición, las señales PASS quedan dominadas por un pico de período cercano a toda la ventana (229 posiciones), que es un efecto de borde/escasez, no una estacionalidad interpretable. En persistencia, el pico dominante de PASS es cercano a 28,6 posiciones y el de FAIL a 32,7; esa diferencia no es estable con este tamaño muestral.

Por tanto, el análisis de Fourier **no encuentra una frecuencia claramente diferente entre problemas que pasan y que fallan**. Lo que separa mejor a las clases es el nivel de incertidumbre en la posición intervenida, especialmente entropía alta y margen bajo. El pico global cercano a 27 posiciones observado en las 1.649 ventanas no debe presentarse como una firma espectral de las soluciones correctas.

## Limitaciones y próximo análisis

1. Falta la secuencia completa token a token por rama; los CSV actuales contienen ventanas y promedios agregados.
2. La interpolación puede crear autocorrelación y picos artificiales.
3. La cantidad de tareas es 20 y no se proporcionan intervalos robustos por tarea para cada posición.
4. La FFT global mezcla tareas con longitudes y estructuras diferentes.
5. No se aplicó un test formal de estacionariedad porque el eje no representa un proceso temporal homogéneo; un ADF/KPSS estándar sería difícil de justificar sin primero definir una unidad de serie por tarea.

Para un análisis temporal confirmatorio, exportar por cada tarea y rama la secuencia completa de entropía, margen, rank del token, tipo léxico, estado parser y resultado de tests. Después ajustar modelos jerárquicos o paneles por tarea, con bootstrap por tarea y validación fuera de muestra.
