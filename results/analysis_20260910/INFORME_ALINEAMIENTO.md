# Validación del lookahead semántico alineado

Fuente: `aligned_semantic_lookahead_validation.zip`, recibido el 10 de septiembre de 2026. Comparación contra la validación congelada anterior sobre los mismos 20 fallos de HumanEval y el mismo modelo Qwen2.5-Coder-7B-Instruct.

## Resultado

El alineamiento corrige el artefacto posicional y cambia materialmente qué posiciones selecciona, pero no cambia la cobertura final: el selector alineado recupera exactamente los mismos 10 de 20 problemas que el selector semántico anterior. La precisión de rama pasa de 15/100 a 17/100.

| Resultado | Semántico anterior | Semántico alineado |
|---|---:|---:|
| Problemas recuperados | 10/20 | 10/20 |
| Tasa | 50% | 50% |
| IC 95% Wilson | 29,9–70,1% | 29,9–70,1% |
| Ramas PASS | 15/100 | 17/100 |
| IC bootstrap 95% de precisión, por problema | 7–24% | 9–26% |

La comparación pareada por problema es idéntica: ambos recuperan diez y fallan en los mismos diez. Esto muestra estabilidad de la cobertura en esta cohorte, pero no equivalencia estadística general entre los selectores.

## Qué corrige el nuevo cálculo

Se excluye el token forzado y se alinean los 11 tokens siguientes mediante Levenshtein de costo unitario. Luego se calculan:

- `aligned_persistence`: distancia de edición normalizada de las continuaciones;
- `aligned_weighted_divergence`: divergencia ponderada sobre pares alineados;
- `anchor_score`: componente léxico estructural anterior;
- `aligned_semantic_score`: promedio de los tres rangos percentiles dentro de cada problema.

Recalculé independientemente las alineaciones desde los IDs y textos originales. Persistencia y divergencia coinciden en las 1.649 posiciones, con error máximo numérico de 1,11 × 10⁻¹⁶. `shift_detected` coincide exactamente con las 679 posiciones donde la persistencia alineada difiere de la comparación posicional.

## Magnitud del efecto del desfase

| Medida | Resultado |
|---|---:|
| Posiciones afectadas | 679/1.649 (41,2%) |
| Posiciones afectadas dentro del nuevo top-5 | 15/100 (15%) |
| Ramas PASS entre esas 15 | 4 |
| Cambio medio de persistencia en las afectadas | −0,593 |
| Cambio medio de divergencia ponderada en las afectadas | −0,294 |

El alineamiento reduce la persistencia media global en 0,244 y la divergencia ponderada en 0,134. La persistencia solo cambia en las 679 posiciones marcadas; la divergencia cambia en 93,6% de las ventanas porque al excluir el token forzado y realinear también cambia el denominador y los pares comparados.

El 41,2% no significa que 41,2% de las conclusiones anteriores fueran incorrectas. Indica que la comparación por índice sobrestimaba la persistencia en esas ventanas según la nueva definición.

## Cambio de selección

Los top-5 anterior y alineado comparten 67/100 posiciones: 3,35 por problema en promedio, con Jaccard medio de 0,531. En HumanEval/32 se reemplazaron las cinco posiciones; en los demás problemas se conservaron entre tres y cinco.

Se incorporaron 33 posiciones y se descartaron 33. De las incorporadas, 27 necesitaron una generación nueva; las otras seis ya existían por haber sido seleccionadas antes por otro método. Las 27 ramas nuevas aportan cuatro PASS. Entre las 33 descartadas había dos PASS. Por eso la densidad sube en dos ramas, aunque la lista de problemas recuperados permanece igual.

La correlación de Spearman entre el score alineado y el anterior es 0,897: el ranking conserva bastante estructura, pero no es el mismo. La correlación con entropía es 0,195 y con margen probabilístico −0,195.

## Recuperación por presupuesto

| Ramas k | Anterior | Alineado | Entropía |
|---:|---:|---:|---:|
| 1 | 5/20 | 4/20 | 8/20 |
| 2 | 7/20 | 6/20 | 10/20 |
| 3 | 7/20 | 8/20 | 10/20 |
| 4 | 8/20 | 8/20 | 10/20 |
| 5 | 10/20 | 10/20 | 10/20 |

El alineado mejora al anterior en k=3, pero queda por debajo en k=1 y k=2. Entropía conserva la ventaja descriptiva con presupuestos pequeños. Como estas curvas se examinan retrospectivamente, no deben usarse para elegir el mejor k y afirmar después que estaba preespecificado.

## Comparaciones pareadas

| Comparación del alineado | Solo alineado / solo comparador | Diferencia | McNemar exacta | Holm, 3 comparaciones |
|---|---:|---:|---:|---:|
| vs. entropía | 1 / 1 | 0 pp | 1,000 | 1,000 |
| vs. margen | 1 / 1 | 0 pp | 1,000 | 1,000 |
| vs. aleatorio | 5 / 1 | +20 pp | 0,21875 | 0,65625 |

La corrección del desfase no aporta evidencia de superioridad sobre entropía o margen. La diferencia observada respecto del control aleatorio sigue siendo interesante, pero la muestra es insuficiente para distinguirla con precisión.

## Controles de calidad

- 1.649 posiciones, 100 selecciones, 100 ramas y 20 problemas; sin claves duplicadas.
- Cinco ramas por problema y coincidencia exacta entre posiciones seleccionadas y ramas evaluadas.
- 73 ramas fueron reutilizadas y 27 generadas de nuevo; la latencia registrada de las nuevas suma 122,3 segundos.
- El reporte agregado coincide con los resultados recalculados desde las ramas.
- Diez scores reconstruidos desde el CSV difieren mínimamente del score exportado; el error máximo es 0,00344. La selección top-5 sigue siendo válida. Esto sugiere empates resueltos con una precisión o regla no retenida completamente en el CSV; conviene exportar los componentes sin redondeo y la clave exacta de desempate.

## Conclusión defendible

> Al alinear las continuaciones, comprobamos que el desfase afectaba la métrica de persistencia en 679 de 1.649 posiciones y cambiaba un tercio del top-5 seleccionado. Aun así, el selector alineado recuperó los mismos 10 de 20 problemas que la versión anterior. La corrección mejora la validez de la señal y eleva ligeramente la densidad de ramas útiles, pero todavía no supera a entropía ni demuestra una ventaja estadística.

La próxima validación debe usar problemas nuevos, congelar esta versión alineada y compararla a presupuesto de ramas y de cómputo constante. También conviene evaluar con HumanEval+ y registrar el alineamiento o sus operaciones para reproducir los empates y casos ambiguos.

