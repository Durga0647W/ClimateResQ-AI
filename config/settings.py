import os
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///climateresq.db")
DEMO_MODE = not bool(NVIDIA_API_KEY)

SIMILARITY_THRESHOLD = 0.35
LOW_CONFIDENCE_THRESH = 0.55
MIN_DESC_LENGTH = 20

SEVERITY_WEIGHTS = {
    "people_affected": 0.35,
    "infrastructure": 0.25,
    "incident_type": 0.25,
    "spread": 0.15,
}

CONFIDENCE_WEIGHTS = {
    "source_reliability": 0.20,
    "cross_source_agreement": 0.25,
    "evidence_strength": 0.20,
    "completeness": 0.20,
    "consistency": 0.15,
}
