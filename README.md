# Ghost Prompt

Experimentos de *retrieval-augmented generation* (RAG) adaptativo para generación de código. El proyecto estudia si intervenir una generación en posiciones de incertidumbre —por ejemplo, explorando la alternativa top-2— permite recuperar soluciones de HumanEval sin presentar resultados exploratorios como conclusiones definitivas.

## Objetivo

El runtime principal implementa y evalúa políticas de recuperación para generación de código: baseline sin recuperación, recuperación estática, disparadores basados en entropía y una política de utilidad aprendida. El modelo generativo y los recuperadores permanecen congelados; la política aprende cuándo conviene intervenir considerando la mejora esperada y el costo.

## Estructura del repositorio

```text
.
├── configs/              Configuraciones reproducibles de las corridas
├── docs/                 Protocolo, guía de Kaggle e informes interpretativos
├── experiments/          Insumos y variantes puntuales de experimentos
├── notebooks/            Cuadernos históricos y de ejecución end-to-end
├── results/              Resultados, figuras, planillas y snapshots analizados
├── scripts/
│   ├── analysis/         Scripts de análisis y diagnósticos
│   ├── kaggle/           Celdas/scripts para ejecutar en Kaggle
│   └── utilities/        Utilidades para construir artefactos
├── src/
│   ├── ghost_prompt/     Runtime principal del proyecto
│   └── adaptive_intervention/  Prototipo de intervención adaptativa
├── tests/                Pruebas automatizadas
└── tools/                Aplicaciones auxiliares, separadas del runtime Python
```

### Dónde encontrar cada cosa

- El flujo experimental está en [docs/experiment_protocol.md](docs/experiment_protocol.md).
- La guía del piloto top-2 está en [docs/kaggle_top2_pilot.md](docs/kaggle_top2_pilot.md).
- Los notebooks experimentales están organizados y documentados en [notebooks/README.md](notebooks/README.md). El notebook original se conserva en `notebooks/archive/` como referencia histórica.
- Los resultados de validación de 20 problemas están en `results/validation_20_problems/`.
- El análisis retrospectivo del 10 de septiembre de 2026, con tablas, figuras, scripts e informes, está en `results/analysis_20260910/`.
- Los informes de lectura rápida están en `docs/reports/`.

## Instalación

Se recomienda Python 3.10 o superior.

```bash
pip install -r requirements.txt
pip install -e .
```

## Flujo reproducible del runtime

Construir un manifiesto versionado del corpus:

```bash
python -m ghost_prompt.cli build-corpus \
  --input-path /ruta/al/corpus.csv \
  --output-dir artifacts/corpora
```

Ejecutar un baseline de HumanEval:

```bash
python -m ghost_prompt.cli run-benchmark \
  --benchmark humaneval \
  --policy-name baseline \
  --config configs/paper_v1.json \
  --num-tasks 32
```

Luego se puede comparar `static`, `entropy`, `entropy_similarity` y `utility`. Para la política aprendida, primero se recolectan contra-factuales y se entrena el estimador:

```bash
python -m ghost_prompt.cli collect-counterfactuals \
  --benchmark humaneval \
  --config configs/paper_v1.json \
  --corpus-manifest artifacts/corpora/<manifest>.json \
  --output-file artifacts/counterfactuals/humaneval.jsonl

python -m ghost_prompt.cli train-utility \
  --examples-file artifacts/counterfactuals/humaneval.jsonl \
  --output-file artifacts/checkpoints/utility.pt
```

Los artefactos generados durante una corrida se escriben en `artifacts/` y no se versionan: pueden ser grandes o contener datos intermedios regenerables. Los resultados consolidados que sustentan los informes sí se conservan en `results/`.

## Resultados y procedencia

Los resultados del repositorio son snapshots locales de trabajo, no una afirmación de superioridad del método. En particular, `results/analysis_20260910/` conserva las fuentes textuales, resultados JSON, figuras y el manifiesto de su análisis.

Las copias descargadas de Drive, con enlaces de origen, fecha y hashes, están documentadas en [results/drive_exports/README.md](results/drive_exports/README.md). Las fuentes de Drive no se modifican desde este proyecto.

## Validación local

```bash
PYTHONPYCACHEPREFIX=/tmp/ghost_prompt_pycache python3 -m py_compile $(find src -name '*.py' | sort)
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Límites actuales

- Los resultados de branching son exploratorios y deben leerse junto con sus auditorías metodológicas.
- `04_frozen_validation.ipynb` contiene la validación principal; `05_hybrid_selector_exploratory.ipynb` y `06_aligned_semantic_review.ipynb` son análisis posteriores. El runtime modular es una implementación complementaria.
- Los scripts de Kaggle requieren preparar allí el modelo y los datos externos indicados en la guía.
