"""
FMA Graph Assembly
LangGraph workflow configuration with integrated Supervisor
"""

import sys
import uuid
from langgraph.graph import StateGraph, END

from fma.config import FMAConfig
from fma.state import FMAState, create_fma_initial_state
from fma.supervisor import create_supervisor_node
from fma.agents.extractor import create_extractor_node
from fma.agents.standardizer import create_standardizer_node
from fma.agents.reporter import create_reporter_node
from fma.agents.db_updater import create_db_updater_node
from fma.agents.graph_updater import create_graph_updater_node
from fma.agents.analyzer import create_analyzer_node


def supervisor_router(state: FMAState) -> str:
    """Route based on Supervisor's decision."""
    next_action = state.get("next_action", "respond")
    
    if next_action == "extract":
        return "extract"
    elif next_action == "analyze":
        return "analyze"
    elif next_action == "done":
        return "done"
    else:
        return "respond"


def extraction_router(state: FMAState) -> str:
    """Route for extraction loop."""
    current_index = state.get("current_md_index", 0)
    md_paths = state.get("md_paths", [])
    
    if current_index < len(md_paths):
        return "continue"
    return "done"


def build_fma_workflow():
    """Build the integrated FMA workflow with Supervisor."""
    workflow = StateGraph(FMAState)
    
    # Create all nodes
    supervisor = create_supervisor_node()
    extractor = create_extractor_node()
    standardizer = create_standardizer_node()
    reporter = create_reporter_node()
    db_updater = create_db_updater_node()
    graph_updater = create_graph_updater_node()
    analyzer = create_analyzer_node()
    
    # Add nodes
    workflow.add_node("Supervisor", supervisor)
    workflow.add_node("Extractor", extractor)
    workflow.add_node("Standardizer", standardizer)
    workflow.add_node("Reporter", reporter)
    workflow.add_node("DBUpdater", db_updater)
    workflow.add_node("GraphUpdater", graph_updater)
    workflow.add_node("Analyzer", analyzer)
    
    # Set entry point
    workflow.set_entry_point("Supervisor")
    
    # Supervisor routing
    workflow.add_conditional_edges(
        "Supervisor",
        supervisor_router,
        {
            "extract": "Extractor",
            "analyze": "Analyzer",
            "respond": END,
            "done": END
        }
    )
    
    # Extraction pipeline
    workflow.add_conditional_edges(
        "Extractor",
        extraction_router,
        {"continue": "Extractor", "done": "Standardizer"}
    )
    
    workflow.add_edge("Standardizer", "Reporter")
    workflow.add_edge("Reporter", "DBUpdater")
    workflow.add_edge("DBUpdater", "GraphUpdater")
    workflow.add_edge("GraphUpdater", "Supervisor")
    
    # Analyzer returns to Supervisor
    workflow.add_edge("Analyzer", "Supervisor")
    
    app = workflow.compile()
    
    return app


def build_extraction_only_workflow():
    """Build extraction-only workflow (legacy --use-fma mode)."""
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
    """Run extraction-only pipeline (legacy mode)."""
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


def run_interactive_session():
    """Run interactive session with integrated Supervisor."""
    print("\n" + "=" * 60)
    print("Feature Mining Agent - Interactive Mode")
    print("=" * 60)
    print("Supervisor Agent가 활성화되었습니다.")
    print("질문을 입력하세요. 종료하려면 'exit' 또는 'quit'을 입력하세요.\n")
    
    app = build_fma_workflow()
    config = {"recursion_limit": 100}
    
    # Initialize state once
    state = create_fma_initial_state()
    state["user_approved"] = True
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q', '종료', '끝']:
                print("\n세션을 종료합니다.")
                break
            
            # Set user request and run workflow
            state["user_request"] = user_input
            
            print("\nSupervisor: ", end="", flush=True)
            
            # Run one iteration
            for event in app.stream(state, config):
                for node_name, node_output in event.items():
                    if node_name == "Supervisor" or node_name == "Analyzer":
                        # Update state with outputs
                        state.update(node_output)
                    elif node_name in ["Extractor", "Standardizer", "Reporter", "DBUpdater", "GraphUpdater"]:
                        # Pipeline nodes
                        state.update(node_output)
                        print(f"\n  [{node_name}] 완료", end="", flush=True)
            
            # Display response
            response = state.get("supervisor_response", "")
            if response:
                print(f"\n{response}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n세션을 종료합니다.")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
