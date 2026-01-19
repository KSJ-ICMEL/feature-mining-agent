"""
Reporter Agent Node
Generates human-readable approval report for HITL
"""

from fma.state import FMAState


def reporter_node(state: FMAState) -> dict:
    print("[Reporter] Generating approval report...")
    
    research_log = state.get("research_log", []).copy()
    mapping_suggestions = state.get("column_mapping_suggestions", {})
    new_cols = state.get("new_columns_to_add", [])
    standardized_data = state.get("standardized_data", {})
    existing_columns = state.get("existing_columns", [])
    
    mapped_msg = "\n".join([f"  - '{k}' -> '{v}'" for k, v in mapping_suggestions.items()])
    new_msg = "\n".join([f"  - '{k}'" for k in new_cols])
    
    data_preview = ""
    for source, entry in list(standardized_data.items())[:3]:
        data_preview += f"\n   [{source}]\n"
        for key, val in entry.items():
            data_preview += f"      {key}: {val}\n"
    
    if len(standardized_data) > 3:
        data_preview += f"\n   ... and {len(standardized_data) - 3} more entries\n"
    
    report = f"""
{'=' * 60}
           SCHEMA EVOLUTION APPROVAL REQUIRED
{'=' * 60}

1. EXISTING DB COLUMNS:
   {', '.join(existing_columns)}

2. AUTO-MAPPED COLUMNS (Vector Search):
{mapped_msg if mapped_msg else "   (None)"}

3. NEW COLUMNS TO CREATE:
{new_msg if new_msg else "   (None)"}

4. DATA PREVIEW:
{data_preview if data_preview else "   (No data)"}

5. SUMMARY:
   - Total files processed: {len(standardized_data)}
   - Columns mapped: {len(mapping_suggestions)}
   - New columns proposed: {len(new_cols)}

{'=' * 60}
"""
    
    print(report)
    research_log.append("Reporter: Report generated")
    
    return {
        "report_message": report,
        "research_log": research_log
    }


def create_reporter_node():
    def node_fn(state: FMAState) -> dict:
        return reporter_node(state)
    return node_fn
