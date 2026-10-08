# Implementation Traceability

| Pipeline stage | Implementation |
|---|---|
| 1 Report Input | `app.py`, `utils/pipeline.py` |
| 2 Report Quality | `services/quality_service.py` |
| 3 GenAI Information Extraction | `services/extraction_service.py`, `services/llm_service.py`, `prompts/extraction_prompt.py` |
| 4 Completeness & Consistency | `services/completeness_service.py` |
| 5 Evidence Verification | `services/evidence_service.py`, `data/supporting_sources.py` |
| 6 Similarity / Duplicate Detection | `services/similarity_service.py` |
| 7 Confidence | `services/confidence_service.py` |
| 8 Severity | `services/severity_service.py` |
| 8 Priority | `services/priority_service.py` |
| 9 Dashboard | `app.py` |
| Human Verification | `app.py`, `database/models.py` |
| AI Assistant | `services/assistant_service.py`, `prompts/assistant_prompt.py` |
| Persistence | `database/models.py`, `database/database.py` |
| Audit trail | `AuditLog` and `VerificationRecord` |

## AI boundary
GenAI is used for information extraction, evidence reasoning and assistant generation. Deterministic Python is used for thresholds, similarity, confidence calculation, severity, priority and routing.
