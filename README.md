# ClimateResQ AI

**GenAI-Powered Climate Disaster Information Verification & Response Assistant**

SDG: **13 – Climate Action**

## Problem
During floods and cyclones, information from citizens and multiple sources can be unstructured, incomplete and duplicated, making it difficult to identify critical incidents quickly.

## Solution
ClimateResQ AI:
- collects disaster reports
- checks report quality
- uses NVIDIA-compatible GenAI/NLP for structured extraction
- checks completeness and consistency
- compares incidents against supporting sources
- detects similar/duplicate reports with TF-IDF + cosine similarity
- calculates explainable confidence, severity and priority
- routes low-confidence/conflicting incidents to human verification
- provides a responder dashboard and database-grounded AI assistant

## Run

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python data/generate_demo_data.py
python -m database.seed
streamlit run app.py
```

NVIDIA is optional. Copy `.env.example` to `.env` and add `NVIDIA_API_KEY` to use the NVIDIA path. Without a key, the deterministic Demo Mode keeps the application usable.

## Important demo note
The supporting sources and 250 report dataset are **SIMULATED DATA** for academic demonstration. They are not real emergency alerts.

## Architecture
Report Input → Quality Check → GenAI Extraction → Completeness/Consistency → Evidence Verification → Similarity/Duplicate Detection → Confidence → Severity/Priority → Human Verification → Responder Dashboard.

## No Agentic AI
ClimateResQ AI intentionally does **not** implement autonomous agents, multi-agent orchestration, autonomous planning, or autonomous external actions. It is a controlled decision-support pipeline with human verification.
