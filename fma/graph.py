"""
FMA Graph Assembly
LangGraph workflow configuration
"""

import sys
import uuid
from langgraph.graph import StateGraph, END

from fma.config import FMAConfig
from fma.state import FMAState, create_fma_initial_state
from fma.agents.extractor import create_extractor_node
from fma.agents.standardizer import create_standardizer_node
from fma.agents.reporter import create_reporter_node
from fma.agents.db_updater import create_db_updater_node
from fma.agents.graph_updater import create_graph_updater_node


def extraction_router(state: FMAState) -> str:
    current_index = state.get("current_md_index", 0)
    md_paths = state.get("md_paths", [])
    
    if current_index < len(md_paths):
        return "continue"
    return "done"


def build_fma_workflow():
    workflow = StateGraph(FMAState)
    
    extractor = create_extractor_node()
    standardizer = create_standardizer_node()
    reporter = create_reporter_node()
    db_updater = create_db_updater_node()
    graph_updater = create_graph_updater_node()
    
    workflow.add_node("Extractor", extractor)
    workflow.add_node("Standardizer", standardizer)
    workflow.add_node("Reporter", reporter)
    workflow.add_node("DBUpdater", db_updater)
    workflow.add_node("GraphUpdater", graph_updater)
    
    workflow.set_entry_point("Extractor")
    
    workflow.add_conditional_edges(
        "Extractor",
        extraction_router,
        {"continue": "Extractor", "done": "Standardizer"}
    )
    
    workflow.add_edge("Standardizer", "Reporter")
    workflow.add_edge("Reporter", "DBUpdater")
    workflow.add_edge("DBUpdater", "GraphUpdater")
    workflow.add_edge("GraphUpdater", END)
    
    app = workflow.compile()
    
    return app


def run_fma_pipeline(app, md_paths: list = None, auto_approve: bool = True):
    config = {"recursion_limit": 100}
    initial_state = create_fma_initial_state(md_paths=md_paths)
    
    if auto_approve:
        initial_state["user_approved"] = True
    
    run_dir = initial_state.get("run_dir", "unknown")
    run_id = initial_state.get("run_id", "unknown")
    
    print(f"\n{'=' * 60}")
    print(f"Feature Mining Agent (FMA) Started")
    print(f"Run ID: {run_id}")
    print(f"Output directory: {run_dir}")
    print(f"Markdown files to analyze: {len(initial_state['md_paths'])}")
    print(f"{'=' * 60}\n")
    
    final_state = None
    try:
        for event in app.stream(initial_state, config):
            for node_name, node_output in event.items():
                print(f"\n--- [{node_name}] Complete ---\n")
                final_state = node_output
        
        print(f"\n{'=' * 60}")
        print("FMA Pipeline Complete")
        
        if final_state:
            csv_path = final_state.get("csv_path", "")
            if csv_path:
                print(f"Results saved to: {csv_path}")
        
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    return final_state
