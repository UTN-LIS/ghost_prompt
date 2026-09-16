# Ghost Prompt

Repositorio de investigación sobre *branching* adaptativo durante la generación de código. Estudia si reemplazar una decisión greedy top-1 por el token top-2, en posiciones seleccionadas sin consultar los tests, puede recuperar soluciones que fallan en HumanEval.

El resultado central es acotado: con hasta cinco ramas por problema, el lookahead semántico, la entropía y el margen top-1/top-2 recuperaron 10 de 20 fallos del baseline; el control aleatorio recuperó 6. La señal semántica aporta posiciones diferentes, pero esta cohorte no demuestra que supere a la entropía.

## Pregunta de investigación

Cuando una generación greedy de código probablemente siga una trayectoria incorrecta, ¿en qué posición conviene bifurcar hacia el segundo token más probable?

El protocolo compara cuatro políticas con el mismo presupuesto de ramas:

| Política | Señal de selección |
|---|---|
| Lookahead semántico | Persistencia, divergencia ponderada y cambios estructurales en una continuación corta |
| Entropía | Incertidumbre de la distribución del siguiente token |
| Margen | Cercanía entre las probabilidades top-1 y top-2 |
| Aleatoria | Control reproducible sin señal de ranking |

Los tests de HumanEval se aplican únicamente después de elegir posiciones y generar las ramas completas. No participan en la selección.

## Estructura

```text
.
├── docs/          Protocolo experimental y guía de ejecución en Kaggle
├── experiments/   Insumos y comparaciones puntuales del experimento
├── notebooks/     Notebooks organizados por fase experimental
└── results/       Checkpoints, resultados, auditorías e informes
```

## Notebooks

El orden y los requisitos de ejecución están documentados en [notebooks/README.md](notebooks/README.md).

| Notebook | Propósito |
|---|---|
| `01_exhaustive_top2_pilot.ipynb` | Piloto exhaustivo sobre `HumanEval/26` |
| `02_entropy_margin_pilot.ipynb` | Comparación de entropía y margen |
| `03_semantic_lookahead_pilot.ipynb` | Desarrollo del selector semántico |
| `04_frozen_validation.ipynb` | Validación principal sobre 20 fallos del baseline |
| `05_hybrid_selector_exploratory.ipynb` | Ensayo híbrido 50/50 de entropía y señal semántica |
| `06_aligned_semantic_review.ipynb` | Revisión con alineación de tokens |

Los notebooks fueron preparados para Kaggle. Requieren una GPU compatible, `Qwen/Qwen2.5-Coder-7B-Instruct` y los checkpoints indicados en la documentación. Las rutas bajo `/kaggle/working/` son rutas de ejecución, no datos del repositorio.

## Resultados principales

La validación congelada usa 20 problemas de HumanEval en los que el baseline greedy falla, un lookahead de 12 tokens y un presupuesto máximo de cinco ramas por política.

| Presupuesto | Semántico | Entropía | Margen | Aleatorio |
|---:|---:|---:|---:|---:|
| 1 rama | 5/20 | 8/20 | 6/20 | 4/20 |
| 2 ramas | 7/20 | 10/20 | 8/20 | 5/20 |
| 3 ramas | 7/20 | 10/20 | 10/20 | 6/20 |
| 4 ramas | 8/20 | 10/20 | 10/20 | 6/20 |
| 5 ramas | 10/20 | 10/20 | 10/20 | 6/20 |

Los artefactos y auditorías principales están en:

- [Protocolo experimental](docs/experiment_protocol.md)
- [Resultados de la validación de 20 problemas](results/validation_20_problems/)
- [Análisis y auditorías del 10 de septiembre de 2026](results/analysis_20260910/)
- [Revisión del selector semántico alineado](results/aligned_semantic_lookahead_20260910/)
- [Ensayo híbrido exploratorio](results/validation_hybrid_20260907/)

## Reproducibilidad y procedencia

Los resultados conservan los checkpoints, selecciones, ramas evaluadas y reportes necesarios para auditar las cifras presentadas. Las exportaciones externas, con su fuente y hash SHA-256, se documentan en [results/drive_exports/README.md](results/drive_exports/README.md).

Para reproducir una fase, abrir el notebook correspondiente en Kaggle, ejecutar las dependencias indicadas en su primera celda y restaurar el checkpoint requerido cuando corresponda. El notebook 04 produce el checkpoint de la validación principal; los notebooks 05 y 06 dependen de esos artefactos.

## Límites

- La cohorte es pequeña: 20 problemas y un único modelo.
- `HumanEval/26` fue excluido de la validación principal porque se usó durante el desarrollo del selector.
- La comparación iguala el número de ramas, no el costo total de cómputo: el lookahead semántico tiene costo adicional.
- Los análisis de posición y Fourier son exploratorios; no justifican una regla periódica de intervención.
- Los tests base de HumanEval se usan para evaluación offline; una publicación final debería incluir una validación independiente adicional, por ejemplo con EvalPlus.

## Cita y uso

Este repositorio se publica como material de investigación exploratoria. Si reutilizás los resultados, citá el repositorio.
