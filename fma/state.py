"""
FMA State Definitions
"""

import os
from typing import Optional, List, Dict, Any, TypedDict
from datetime import datetime
from pydantic import BaseModel, Field

from fma.config import FMAConfig


class ExtractedValue(BaseModel):
    value: Any = Field(..., description="Extracted numeric or string value")
    unit: Optional[str] = Field(None, description="Unit (e.g., S/cm, MPa)")
    original_text: Optional[str] = Field(None, description="Original text from paper")


class PaperAnalysisData(BaseModel):
    doi: str = Field(default="", description="Paper DOI")
    material_id: str = Field(default="", description="Material composition identifier")
    features: Dict[str, ExtractedValue] = Field(default_factory=dict)
    source_file: str = Field(default="", description="Source markdown file")


class FMAState(TypedDict):
    # Supervisor state
    messages: List[Any]
    user_request: str
    next_action: str  # "extract", "analyze", "respond", "done"
    supervisor_response: str
    
    # Extraction pipeline state
    md_paths: List[str]
    current_md_index: int
    
    existing_columns: List[str]
    column_embeddings: Dict[str, List[float]]
    
    all_extracted_data: List[dict]
    current_extracted: Optional[dict]
    
    standardized_data: Dict[str, Any]
    column_mapping_suggestions: Dict[str, str]
    new_columns_to_add: List[str]
    
    # Analysis state
    analysis_result: str
    
    report_message: str
    user_approved: bool
    
    run_id: str
    run_dir: str
    csv_path: str
    status: str
    research_log: List[str]


def create_run_directory(run_id: str) -> str:
    run_dir = os.path.join(FMAConfig.RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def create_fma_initial_state(md_paths: List[str] = None, run_id: str = None) -> FMAState:
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = create_run_directory(run_id)
    
    if md_paths is None:
        md_dir = FMAConfig.MD_DIRECTORY
        if os.path.exists(md_dir):
            md_paths = [
                os.path.join(md_dir, f) for f in os.listdir(md_dir)
                if f.lower().endswith('.md')
            ]
        else:
            md_paths = []
    
    csv_path = os.path.join(run_dir, "extracted_features.csv")
    
    return {
        # Supervisor state
        "messages": [],
        "user_request": "",
        "next_action": "",
        "supervisor_response": "",
        
        # Extraction pipeline state
        "md_paths": md_paths,
        "current_md_index": 0,
        
        "existing_columns": FMAConfig.EXISTING_COLUMNS.copy(),
        "column_embeddings": {},
        
        "all_extracted_data": [],
        "current_extracted": None,
        
        "standardized_data": {},
        "column_mapping_suggestions": {},
        "new_columns_to_add": [],
        
        # Analysis state
        "analysis_result": "",
        
        "report_message": "",
        "user_approved": False,
        
        "run_id": run_id,
        "run_dir": run_dir,
        "csv_path": csv_path,
        "status": "running",
        "research_log": [f"--- FMA Run {run_id} Started ---"],
    }
