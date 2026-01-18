"""
PDF Extractor Node
Extract control variables, manipulated variables, and ionic conductivity from PDF
"""

import os
import json
import pymupdf4llm
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

from kokoa.config import Config
from kokoa.state import AgentState


class ExperimentData(BaseModel):
    composition: str = Field(description="Solid electrolyte composition (e.g., Li7La3Zr2O12)")
    ionic_conductivity: float = Field(description="Ionic conductivity value in S/cm")
    ionic_conductivity_unit: str = Field(default="S/cm", description="Ionic conductivity unit")
    control_variables: dict = Field(description="Control variables (e.g., temperature, measurement method)")
    manipulated_variables: dict = Field(description="Manipulated variables (e.g., dopant, sintering temperature)")
    measurement_temperature: Optional[float] = Field(default=None, description="Measurement temperature (K)")


class ExtractionResult(BaseModel):
    experiments: List[ExperimentData] = Field(description="List of extracted experiment data")
    paper_title: Optional[str] = Field(default=None, description="Paper title")
    doi: Optional[str] = Field(default=None, description="DOI")


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert in analyzing solid electrolyte ionic conductivity research papers.

Extract the following information from the given paper text:
1. Solid electrolyte composition (chemical formula)
2. Ionic conductivity value (convert to S/cm)
3. Control variables (conditions kept constant in the experiment)
4. Manipulated variables (conditions intentionally varied in the experiment)
5. Measurement temperature

Extract all experimental conditions and results without omission.
Respond in JSON format only."""),
    ("user", """Paper text:
{paper_text}

Extract solid electrolyte ionic conductivity data from the above paper.""")
])


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        md_text = pymupdf4llm.to_markdown(pdf_path)
        return md_text
    except Exception as e:
        print(f"   [ERROR] PDF text extraction failed: {e}")
        return ""


def pdf_extractor_node(state: AgentState) -> dict:
    print("[PDF Extractor] Starting PDF analysis...")
    
    pdf_paths = state.get("pdf_paths", [])
    current_index = state.get("current_pdf_index", 0)
    extracted_data = state.get("extracted_data", []).copy()
    research_log = state.get("research_log", []).copy()
    
    if current_index >= len(pdf_paths):
        print("   [DONE] All PDFs processed")
        return {
            "status": "extraction_complete",
            "research_log": research_log + ["PDF Extractor: All PDFs processed"]
        }
    
    pdf_path = pdf_paths[current_index]
    print(f"   Processing: {os.path.basename(pdf_path)} ({current_index + 1}/{len(pdf_paths)})")
    
    paper_text = extract_text_from_pdf(pdf_path)
    if not paper_text:
        research_log.append(f"PDF Extractor: Failed to extract {os.path.basename(pdf_path)}")
        return {
            "current_pdf_index": current_index + 1,
            "research_log": research_log
        }
    
    if len(paper_text) > 15000:
        paper_text = paper_text[:15000] + "\n\n[... text truncated ...]"
    
    llm = ChatOllama(
        model=Config.MODEL_NAME,
        temperature=0.1
    )
    
    parser = JsonOutputParser(pydantic_object=ExtractionResult)
    chain = EXTRACTION_PROMPT | llm | parser
    
    try:
        print("   [LLM] Analyzing...")
        result = chain.invoke({"paper_text": paper_text})
        
        for exp in result.get("experiments", []):
            extracted_data.append({
                "composition": exp.get("composition", ""),
                "ionic_conductivity": exp.get("ionic_conductivity", 0.0),
                "features": {
                    **exp.get("control_variables", {}),
                    **exp.get("manipulated_variables", {})
                },
                "source_pdf": os.path.basename(pdf_path)
            })
        
        exp_count = len(result.get("experiments", []))
        print(f"   [DONE] Extracted {exp_count} experiments")
        research_log.append(f"PDF Extractor: Extracted {exp_count} experiments from {os.path.basename(pdf_path)}")
        
    except Exception as e:
        print(f"   [ERROR] Extraction failed: {e}")
        research_log.append(f"PDF Extractor: Error - {str(e)[:100]}")
    
    return {
        "current_pdf_index": current_index + 1,
        "extracted_data": extracted_data,
        "research_log": research_log
    }


def create_pdf_extractor_node():
    def node_fn(state: AgentState) -> dict:
        return pdf_extractor_node(state)
    return node_fn
