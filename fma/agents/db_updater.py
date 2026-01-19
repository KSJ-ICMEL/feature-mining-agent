"""
DB Updater Agent Node
Saves standardized data to CSV
"""

import os
import csv
from fma.state import FMAState


def db_updater_node(state: FMAState) -> dict:
    print("[DB Updater] Saving data...")
    
    research_log = state.get("research_log", []).copy()
    user_approved = state.get("user_approved", False)
    standardized_data = state.get("standardized_data", {})
    csv_path = state.get("csv_path", "")
    mapping_suggestions = state.get("column_mapping_suggestions", {})
    new_cols = state.get("new_columns_to_add", [])
    existing_columns = state.get("existing_columns", [])
    
    if not user_approved:
        print("   [SKIP] User approval not granted")
        return {
            "status": "cancelled",
            "research_log": research_log + ["DB Updater: Cancelled - no approval"]
        }
    
    if not standardized_data:
        print("   [SKIP] No data to save")
        return {
            "status": "no_data",
            "research_log": research_log + ["DB Updater: No data to save"]
        }
    
    all_columns = ["source_file", "doi", "material_id"]
    all_columns.extend([v for v in mapping_suggestions.values()])
    all_columns.extend(new_cols)
    all_columns = list(dict.fromkeys(all_columns))
    
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_columns, extrasaction='ignore')
            writer.writeheader()
            
            for source, entry in standardized_data.items():
                row = {"source_file": source}
                row.update(entry)
                writer.writerow(row)
        
        print(f"   [DONE] Saved {len(standardized_data)} entries to {csv_path}")
        research_log.append(f"DB Updater: Saved to {csv_path}")
        
        return {
            "status": "complete",
            "csv_path": csv_path,
            "research_log": research_log
        }
        
    except Exception as e:
        print(f"   [ERROR] Failed to save: {e}")
        return {
            "status": "error",
            "research_log": research_log + [f"DB Updater: Error - {e}"]
        }


def create_db_updater_node():
    def node_fn(state: FMAState) -> dict:
        return db_updater_node(state)
    return node_fn
