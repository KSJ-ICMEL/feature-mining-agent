"""
KOKOA Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class Config:
    MODEL_NAME = "gpt-oss:120b"
    TEMPERATURE = 0.1
    
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    
    EMBEDDING_MODEL = "BAAI/bge-m3"
    EMBEDDING_DEVICE = get_device()
    K_RETRIEVAL = 3
    
    MAX_LOOPS = 10
    MAX_RESEARCH_ATTEMPTS = 3
    
    INITIAL_STATE_DIR = os.path.join(_PROJECT_ROOT, "initial_state")
    RUNS_DIR = os.path.join(_PROJECT_ROOT, "runs")
    
    PERSIST_DIRECTORY = os.path.join(_PROJECT_ROOT, "initial_state", "chroma_store")
    PDF_DIRECTORY = os.path.join(_PROJECT_ROOT, "initial_state", "pdf")
    CSV_OUTPUT_PATH = os.path.join(_PROJECT_ROOT, "data", "ionic_conductivity.csv")
    
    CHUNK_SIZE = 1200
    CHUNK_OVERLAP = 300
    
    ARXIV_MAX_DOCS = 3
    
    @classmethod
    def from_env(cls):
        config = cls()
        config.MODEL_NAME = os.getenv("KOKOA_MODEL", config.MODEL_NAME)
        config.PERSIST_DIRECTORY = os.getenv("KOKOA_CHROMA_DIR", config.PERSIST_DIRECTORY)
        config.EMBEDDING_DEVICE = os.getenv("KOKOA_DEVICE", config.EMBEDDING_DEVICE)
        return config
