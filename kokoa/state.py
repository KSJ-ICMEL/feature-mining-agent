"""
Feature Mining Agent State Definitions
"""

import os
import json
from typing import Optional, List, TypedDict
from datetime import datetime

from kokoa.config import Config


class ExtractedData(TypedDict):
    composition: str
    ionic_conductivity: float
    features: dict
    source_pdf: str


class AgentState(TypedDict):
    pdf_paths: List[str]
    current_pdf_index: int
    extracted_data: List[ExtractedData]
    
    csv_path: str
    knowledge_graph_updated: bool
    
    proposed_features: List[str]
    selected_feature: str
    
    arxiv_results: List[dict]
    downloaded_pdfs: List[str]
    
    iteration_count: int
    max_iterations: int
    status: str
    
    run_id: str
    run_dir: str
    research_log: List[str]


def create_run_directory(run_id: str) -> str:
    run_dir = os.path.join(Config.RUNS_DIR, run_id)
    
    os.makedirs(os.path.join(run_dir, "pdf"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "data"), exist_ok=True)
    
    return run_dir


def create_initial_state(pdf_paths: List[str] = None, run_id: str = None) -> AgentState:
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = create_run_directory(run_id)
    
    if pdf_paths is None:
        pdf_dir = Config.PDF_DIRECTORY
        if os.path.exists(pdf_dir):
            pdf_paths = [
                os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) 
                if f.lower().endswith('.pdf')
            ]
        else:
            pdf_paths = []
    
    csv_path = os.path.join(run_dir, "data", "ionic_conductivity.csv")
    
    return {
        "pdf_paths": pdf_paths,
        "current_pdf_index": 0,
        "extracted_data": [],
        
        "csv_path": csv_path,
        "knowledge_graph_updated": False,
        
        "proposed_features": [],
        "selected_feature": "",
        
        "arxiv_results": [],
        "downloaded_pdfs": [],
        
        "iteration_count": 0,
        "max_iterations": Config.MAX_LOOPS,
        "status": "running",
        
        "run_id": run_id,
        "run_dir": run_dir,
        "research_log": [f"--- Run {run_id} Started ---"],
    }
