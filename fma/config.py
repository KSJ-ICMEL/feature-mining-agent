"""
FMA Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()


class FMAConfig:
    MODEL_NAME = os.getenv("FMA_MODEL", "gpt-oss:120b")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    RUNS_DIR = os.path.join(BASE_DIR, "runs")
    os.makedirs(RUNS_DIR, exist_ok=True)
    
    MD_DIRECTORY = os.path.join(BASE_DIR, "example", "papers", "argyrodite")
    
    VECTOR_SIMILARITY_THRESHOLD = 0.85
    
    EXISTING_COLUMNS = [
        "Ionic_Conductivity_mS_cm",
        "Activation_Energy_eV", 
        "Sintering_Temp",
        "Ball_Milling_RPM",
        "Grain_Size_um",
        "Relative_Density"
    ]
