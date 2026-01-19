"""
Extractor Agent Node
Reads markdown files and extracts structured data using LLM
"""

import os
import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional

from fma.config import FMAConfig
from fma.state import FMAState, PaperAnalysisData, ExtractedValue


class ExtractionResult(BaseModel):
    doi: str = Field(default="", description="Paper DOI")
    material_id: str = Field(default="", description="Material composition (e.g., Li6PS5Cl)")
    ionic_conductivity: Optional[float] = Field(None, description="Ionic conductivity value")
    ionic_conductivity_unit: str = Field(default="S/cm", description="Conductivity unit")
    activation_energy: Optional[float] = Field(None, description="Activation energy (eV)")
    sintering_temp: Optional[float] = Field(None, description="Sintering temperature (C)")
    ball_milling_rpm: Optional[float] = Field(None, description="Ball milling speed (rpm)")
    additional_features: Dict[str, Any] = Field(default_factory=dict, description="Other extracted features")


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert in analyzing solid electrolyte ionic conductivity research papers.

Extract the following information from the given markdown text:
1. DOI (if available)
2. Material composition (chemical formula like Li6PS5Cl)
3. Ionic conductivity value and unit
4. Activation energy (eV)
5. Sintering temperature (C)
6. Ball milling speed (rpm)
7. Any other relevant experimental parameters

Respond ONLY in valid JSON format matching this structure:
{{
    "doi": "10.xxxx/...",
    "material_id": "Li6PS5Cl",
    "ionic_conductivity": 3.6e-3,
    "ionic_conductivity_unit": "S/cm",
    "activation_energy": 0.30,
    "sintering_temp": 550,
    "ball_milling_rpm": 500,
    "additional_features": {{"grain_size": 10, "relative_density": 95}}
}}

If a value is not found, use null."""),
    ("user", """Paper markdown text:
{paper_text}

Extract all solid electrolyte ionic conductivity data from the above paper.""")
])


def read_markdown_file(md_path: str) -> str:
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"   [ERROR] Failed to read {md_path}: {e}")
        return ""


def extractor_node(state: FMAState) -> dict:
    print("[Extractor] Reading and analyzing markdown files...")
    
    md_paths = state.get("md_paths", [])
    current_index = state.get("current_md_index", 0)
    all_extracted = state.get("all_extracted_data", []).copy()
    research_log = state.get("research_log", []).copy()
    
    if current_index >= len(md_paths):
        print("   [DONE] All markdown files processed")
        return {
            "status": "extraction_complete",
            "research_log": research_log + ["Extractor: All files processed"]
        }
    
    md_path = md_paths[current_index]
    filename = os.path.basename(md_path)
    print(f"   Processing: {filename} ({current_index + 1}/{len(md_paths)})")
    
    paper_text = read_markdown_file(md_path)
    if not paper_text:
        research_log.append(f"Extractor: Failed to read {filename}")
        return {
            "current_md_index": current_index + 1,
            "research_log": research_log
        }
    
    llm = ChatOllama(
        model=FMAConfig.MODEL_NAME,
        temperature=0.1
    )
    
    parser = JsonOutputParser(pydantic_object=ExtractionResult)
    chain = EXTRACTION_PROMPT | llm | parser
    
    try:
        print("   [LLM] Analyzing...")
        result = chain.invoke({"paper_text": paper_text})
        
        extracted_entry = {
            "doi": result.get("doi", filename.replace(".md", "")),
            "material_id": result.get("material_id", ""),
            "features": {},
            "source_file": filename
        }
        
        if result.get("ionic_conductivity") is not None:
            extracted_entry["features"]["ionic_cond"] = {
                "value": result["ionic_conductivity"],
                "unit": result.get("ionic_conductivity_unit", "S/cm")
            }
        
        if result.get("activation_energy") is not None:
            extracted_entry["features"]["act_energy"] = {
                "value": result["activation_energy"],
                "unit": "eV"
            }
        
        if result.get("sintering_temp") is not None:
            extracted_entry["features"]["sintering_T"] = {
                "value": result["sintering_temp"],
                "unit": "C"
            }
        
        if result.get("ball_milling_rpm") is not None:
            extracted_entry["features"]["milling_spd"] = {
                "value": result["ball_milling_rpm"],
                "unit": "rpm"
            }
        
        for key, val in result.get("additional_features", {}).items():
            if val is not None:
                extracted_entry["features"][key] = {"value": val, "unit": ""}
        
        all_extracted.append(extracted_entry)
        
        feature_count = len(extracted_entry["features"])
        print(f"   [DONE] Extracted {feature_count} features")
        research_log.append(f"Extractor: {feature_count} features from {filename}")
        
    except Exception as e:
        print(f"   [ERROR] Extraction failed: {e}")
        research_log.append(f"Extractor: Error - {str(e)[:100]}")
    
    return {
        "current_md_index": current_index + 1,
        "all_extracted_data": all_extracted,
        "current_extracted": extracted_entry if 'extracted_entry' in dir() else None,
        "research_log": research_log
    }


def create_extractor_node():
    def node_fn(state: FMAState) -> dict:
        return extractor_node(state)
    return node_fn
