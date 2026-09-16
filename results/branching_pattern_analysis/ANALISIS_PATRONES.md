# Análisis exploratorio de patrones de branching

## Conclusión ejecutiva

Los resultados contienen una señal prometedora: una única sustitución top-1 → top-2 puede llevar una trayectoria greedy fallida a una solución correcta, y las recuperaciones no aparecen uniformemente. Se concentran en decisiones tempranas, con incertidumbre relativamente alta y con cambios que alteran de forma persistente la continuación.

Sin embargo, el experimento todavía no demuestra superioridad sobre entropía o margen. Los tres selectores recuperaron 10 de 20 problemas y la comparación semántico vs. entropía fue 1 caso exclusivo contra 1 caso exclusivo. Además, hay un defecto de evaluación que obliga a repetir parte del experimento antes de usar las tasas en un artículo.

## Auditoría de validez

El evaluador aplica `extract_code()` y conserva solamente la función objetivo generada. HumanEval exige evaluar el prompt completo más la completion; algunos prompts contienen funciones auxiliares anteriores a la función objetivo. Al descartarlas se produjeron cuatro `NameError` en HumanEval/10, /32, /38 y /50.

Por tanto:

- esos cuatro resultados no permiten medir recuperabilidad;
- 1.649 posiciones sin rama completa no son fallos, sino posiciones no evaluadas;
- las 255 ramas evaluadas fueron elegidas por los selectores y constituyen una muestra sesgada;
- la unidad estadística independiente es el problema, no cada rama;
- 2 de 1.649 lookaheads no reprodujeron exactamente el par guardado, pero ninguno fue seleccionado para generar una rama completa.

La corrección mínima es evaluar `task.prompt + completion + task.test`, sin volver a insertar una función completa extraída. Después debe reconstruirse la cohorte de 20 fallos desde cero.

## Hallazgos descriptivos

### Recuperación

- 255 ramas completas evaluadas; 29 pasaron los tests base.
- 11 de 20 problemas tuvieron al menos una rama seleccionada que pasó.
- Semántico: 10/20; entropía: 10/20; margen: 10/20; aleatorio: 6/20.
- Semántico y entropía coincidieron en 9 recuperaciones. HumanEval/121 fue exclusivo del semántico y HumanEval/95 exclusivo de entropía.
- Entropía y margen escogieron 93 de 100 posiciones en común: en este experimento son casi el mismo selector.
- Semántico y entropía coincidieron sólo en 34 de 100 posiciones. El selector semántico sí explora otra región, aunque todavía no mejora la cantidad final de problemas recuperados.

### Posición de la bifurcación

- Primer cuarto de la generación: 15/84 ramas pasaron (17,9%).
- Segundo cuarto: 10/78 (12,8%).
- Tercer cuarto: 2/66 (3,0%).
- Último cuarto: 2/27 (7,4%).

Las ramas exitosas tuvieron posición normalizada mediana 0,24 frente a 0,43 en las fallidas. Con un presupuesto fijo de cinco ramas, conviene priorizar el primer 40% de la trayectoria, pero conservar una cuota semántica para excepciones tardías.

### Señales del token y de la continuación

Comparando las 29 ramas PASS con las 226 FAIL:

| Señal | Mediana PASS | Mediana FAIL | Lectura |
|---|---:|---:|---|
| Entropía | 0,656 | 0,0047 | PASS aparece más en puntos inciertos |
| Margen de probabilidad | 0,584 | 0,999 | menor margen favorece recuperación |
| Score semántico | 0,792 | 0,676 | señal complementaria moderada |
| Divergencia semántica | 0,558 | 0,496 | el desvío útil cambia la continuación |
| Anchor score | 0,512 | 0,372 | los cambios estructurales importan |
| Distancia de edición | 0,917 | 0,625 | las ramas exitosas suelen reescribir más |

La entropía tuvo AUC univariada exploratoria 0,766; score semántico 0,662. Un filtro retrospectivo `entropía ≥ 0,5`, `margen ≤ 0,6` y posición ≤ 40% obtuvo 12 PASS en 34 ramas (35,3%), pero es una regla descubierta sobre estos mismos datos: debe congelarse y validarse en problemas nuevos.

### Tipo de transición

Las transiciones con mayor soporte útil fueron:

- identificador → keyword: 6/13 PASS (46,2%);
- keyword → keyword: 4/15 (26,7%);
- identificador → identificador: 4/49 (8,2%);
- puntuación → puntuación: 3/45 (6,7%).

Esto sugiere que el efecto interesante no es corregir un carácter aislado. Forzar tokens como `if`, `return` o `def` puede cambiar el régimen de generación y hacer que el modelo reconstruya el algoritmo restante. Esa “bifurcación estructural persistente” es una hipótesis más defendible que llamar punto de inflexión a cualquier punto de entropía alta.

### Dos excepciones informativas

**HumanEval/121 — sólo semántico.** El baseline usó índices impares y valores impares. En la posición 20 el cambio top-1 `2` → top-2 espacio llevó a regenerar la condición correcta: índices pares y valores impares. La entropía era prácticamente cero y el margen casi uno, por lo que un selector de incertidumbre nunca lo priorizaría. Este caso demuestra que “confianza alta” no implica “decisión causalmente irrelevante”.

**HumanEval/95 — sólo entropía.** La rama exitosa de entropía reemplazó `all` por `if` y regeneró una guarda explícita que comprueba que todas las claves sean strings antes de evaluar mayúsculas/minúsculas. Aquí la incertidumbre local sí marca el punto adecuado y el ranking semántico lo omitió.

## Patrón entre problemas detectados y no detectados

- Los problemas recuperados tuvieron baseline mediano de 59 tokens; los no recuperados, 112.
- Con cinco ramas por selector, las trayectorias largas quedan mucho menos cubiertas.
- 8 de 12 fallos tipo `AssertionError` fueron recuperados; los cuatro `NameError` no, pero estos últimos están contaminados por el defecto del evaluador.
- La complejidad AST total de la solución canónica fue casi idéntica entre grupos. En esta muestra, la longitud de la trayectoria parece más relevante que la dificultad estructural del problema.
- Las listas tuvieron 3/4 recuperaciones, frente a 4/8 en strings y 4/8 en numeric; las celdas son demasiado pequeñas para afirmar un efecto por dominio.

## Selector candidato para la próxima validación

Usar un selector híbrido pre-registrado, sin ajustar sus umbrales sobre el nuevo conjunto:

1. reservar tres ramas para posiciones del primer 40% con entropía alta y margen bajo;
2. reservar dos ramas para score semántico alto, permitiendo posiciones tardías y margen alto;
3. penalizar duplicados entre entropía y margen, porque actualmente se solapan 93%;
4. registrar métricas por presupuesto `k = 1..5` y comparar a nivel problema;
5. ejecutar HumanEval+ además de los tests base.

La pregunta publicable quedaría: **¿un selector híbrido que combina incertidumbre local y divergencia contrafactual persistente alcanza la misma o mayor recuperación que entropía con menos ramas completas?** La contribución útil sería ahorro de cómputo con cobertura complementaria, no sólo una nueva fórmula de score.

## Archivos reproducibles

- `analysis_summary.json`: resumen de hallazgos.
- `problem_features.csv`: una fila por problema.
- `branch_features.csv`: una fila por rama completa.
- `passing_branch_examples.csv`: ejemplos PASS con snippets.
- `pass_fail_metric_comparison.csv`: medianas, AUC exploratoria y Cliff's delta.
- `analyze_branching_patterns.py`: script que genera las tablas anteriores.
