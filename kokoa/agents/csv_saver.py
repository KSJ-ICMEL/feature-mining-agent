"""
CSV Saver Node
Save extracted data to CSV
"""

import os
import csv
from typing import List
from langchain_core.tools import tool

from kokoa.config import Config
from kokoa.state import AgentState


@tool
def append_to_csv(csv_path: str, rows: List[dict]) -> str:
    """Append data rows to CSV file
    
    Args:
        csv_path: CSV file path
        rows: List of data rows (dict format)
    
    Returns:
        Result message
    """
    if not rows:
        return "No data to append"
    
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    file_exists = os.path.exists(csv_path)
    
    all_keys = set()
    for row in rows:
        all_keys.update(row.keys())
        if "features" in row and isinstance(row["features"], dict):
            all_keys.update(row["features"].keys())
            all_keys.discard("features")
    
    base_cols = ["composition", "ionic_conductivity", "source_pdf"]
    feature_cols = sorted([k for k in all_keys if k not in base_cols])
    fieldnames = base_cols + feature_cols
    
    if file_exists:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_cols = reader.fieldnames or []
            for col in feature_cols:
                if col not in existing_cols:
                    existing_cols.append(col)
            fieldnames = existing_cols
    
    flat_rows = []
    for row in rows:
        flat_row = {
            "composition": row.get("composition", ""),
            "ionic_conductivity": row.get("ionic_conductivity", ""),
            "source_pdf": row.get("source_pdf", "")
        }
        if "features" in row and isinstance(row["features"], dict):
            flat_row.update(row["features"])
        flat_rows.append(flat_row)
    
    mode = 'a' if file_exists else 'w'
    with open(csv_path, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerows(flat_rows)
    
    return f"Appended {len(flat_rows)} rows to {csv_path}"


def csv_saver_node(state: AgentState) -> dict:
    print("[CSV Saver] Saving data...")
    
    extracted_data = state.get("extracted_data", [])
    csv_path = state.get("csv_path", Config.CSV_OUTPUT_PATH)
    research_log = state.get("research_log", []).copy()
    
    if not extracted_data:
        print("   [WARN] No data to save")
        return {
            "research_log": research_log + ["CSV Saver: No data to save"]
        }
    
    try:
        result = append_to_csv.invoke({
            "csv_path": csv_path,
            "rows": extracted_data
        })
        print(f"   [DONE] {result}")
        research_log.append(f"CSV Saver: {result}")
        
    except Exception as e:
        print(f"   [ERROR] Save failed: {e}")
        research_log.append(f"CSV Saver: Error - {str(e)[:100]}")
    
    return {
        "csv_path": csv_path,
        "research_log": research_log
    }


def create_csv_saver_node():
    def node_fn(state: AgentState) -> dict:
        return csv_saver_node(state)
    return node_fn
