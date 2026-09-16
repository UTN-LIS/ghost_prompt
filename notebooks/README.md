# Notebooks experimentales

Esta carpeta contiene los notebooks públicos del proyecto de branching top-2 sobre HumanEval. El código de las celdas se conserva sin modificaciones respecto del notebook original; la reorganización sólo separa los experimentos por objetivo.

## Orden recomendado

Los experimentos deben ejecutarse en este orden:

1. `01_exhaustive_top2_pilot.ipynb` — piloto exhaustivo sobre `HumanEval/26`.
2. `02_entropy_margin_pilot.ipynb` — comparación de entropía y margen top-1/top-2.
3. `03_semantic_lookahead_pilot.ipynb` — piloto del selector semántico.
4. `04_frozen_validation.ipynb` — validación congelada sobre 20 problemas.
5. `05_hybrid_selector_exploratory.ipynb` — combinación 50/50 de entropía y señal semántica.
6. `06_aligned_semantic_review.ipynb` — revisión del selector semántico con alineación de tokens.

Los notebooks 5 y 6 requieren un checkpoint completo de la validación del notebook 4. El notebook 5 conserva además las definiciones de esa validación para poder verificar la compatibilidad del checkpoint, pero el ensayo híbrido sólo comienza cuando la validación original está completa. Es exploratorio y no la reemplaza.

## Ejecución

Los notebooks fueron preparados para Kaggle y esperan una GPU compatible, el modelo `Qwen/Qwen2.5-Coder-7B-Instruct` y los artefactos indicados en la documentación. Las rutas `/kaggle/working/` son rutas de ejecución de Kaggle, no datos versionados del repositorio.

Antes de ejecutar los notebooks 4–6, completar la corrida anterior o cargar su checkpoint correspondiente. Las pruebas de HumanEval se ejecutan después de seleccionar las posiciones y no participan en el ranking.

## Archivos

- `01`–`03`: pilotos de desarrollo.
- `04`: experimento principal de validación.
- `05`: análisis exploratorio posterior.
- `06`: revisión metodológica posterior.
- `archive/experiments_3_main_raw.ipynb`: notebook original conservado como referencia histórica.

La metodología general está documentada en [`../docs/experiment_protocol.md`](../docs/experiment_protocol.md). La guía del piloto inicial está en [`../docs/kaggle_top2_pilot.md`](../docs/kaggle_top2_pilot.md).
