# Ghost Prompt RAG for Code Generation

> **Under Development**: Code may change. Anyone can run the demo [demo.ipynb](demo.ipynb) on Kaggle as it is with the dataset. But notice that implementation may change, not so the objective of improving performance.

Adaptive RAG experiment that injects “ghost” prompts mid-generation when token-level entropy spikes. Retrieval combines BM25 + dense embeddings with Reciprocal Rank Fusion, then evaluates against HumanEval.

## Quickstart
- Python 3.12.12, CUDA GPU recommended.
- Install deps: `pip install -r requirements.txt`.

## Data
- HumanEval is pulled automatically via `datasets`.
- Retrieval corpus: download the Kaggle CSV (combined_problems_final.csv) and set `CORPUS_CSV`. If missing, the pipeline continues with an empty corpus; RAG retrieval becomes a no-op but baseline generation still runs.

## Reproducibility
- `set_seed` is applied (Python, NumPy, Torch, CUDA) and can be overridden with `SEED`.
- For stricter determinism, enable `torch.backends.cudnn.deterministic = True` inside the notebook.

## Running
1) Install dependencies.
2) Open and run [demo.ipynb](demo.ipynb) end to end. The main orchestration cell handles dataset loading, retrieval setup, and generation/evaluation.

## Outputs
- `experiments.jsonl` collects per-task generations, metrics, and evaluation results.
- Analysis helpers render pass/fail breakdowns and side-by-side code comparisons inside the notebook.

## Hardware Recommendations
- This project was originally tested on two T4 GPUs using Python 3.12.12 on Kaggle.
