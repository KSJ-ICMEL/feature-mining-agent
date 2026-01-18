"""
Feature Mining Agent Graph Assembly
LangGraph workflow configuration
"""

import sys
import uuid
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from kokoa.config import Config
from kokoa.state import AgentState, create_initial_state
from kokoa.agents.pdf_extractor import create_pdf_extractor_node
from kokoa.agents.csv_saver import create_csv_saver_node
from kokoa.agents.knowledge_graph import create_knowledge_graph_node
from kokoa.agents.feature_reasoner import create_feature_reasoner_node
from kokoa.agents.arxiv_searcher import create_arxiv_searcher_node


class TeeWriter:
    def __init__(self, file_path):
        self.file = open(file_path, 'w', encoding='utf-8')
        self.stdout = sys.stdout
    
    def write(self, data):
        self.stdout.write(data)
        self.stdout.flush()
        self.file.write(data)
        self.file.flush()
    
    def flush(self):
        self.stdout.flush()
        self.file.flush()
    
    def close(self):
        self.file.close()


def pdf_extraction_router(state: AgentState) -> str:
    current_index = state.get("current_pdf_index", 0)
    pdf_paths = state.get("pdf_paths", [])
    
    if current_index < len(pdf_paths):
        return "continue_extraction"
    return "extraction_done"


def arxiv_router(state: AgentState) -> str:
    status = state.get("status", "")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", Config.MAX_LOOPS)
    
    if iteration_count >= max_iterations:
        print(f"[System] Max iterations ({max_iterations}) reached. Terminating.")
        return "end"
    
    if status == "loop_continue":
        print("[System] New PDFs downloaded. Returning to PDF Extractor.")
        return "loop"
    
    return "end"


def build_workflow():
    workflow = StateGraph(AgentState)
    
    pdf_extractor = create_pdf_extractor_node()
    csv_saver = create_csv_saver_node()
    knowledge_graph = create_knowledge_graph_node()
    feature_reasoner = create_feature_reasoner_node()
    arxiv_searcher = create_arxiv_searcher_node()
    
    workflow.add_node("PDFExtractor", pdf_extractor)
    workflow.add_node("CSVSaver", csv_saver)
    workflow.add_node("KnowledgeGraph", knowledge_graph)
    workflow.add_node("FeatureReasoner", feature_reasoner)
    workflow.add_node("ArxivSearcher", arxiv_searcher)
    
    workflow.set_entry_point("PDFExtractor")
    
    workflow.add_conditional_edges(
        "PDFExtractor",
        pdf_extraction_router,
        {"continue_extraction": "PDFExtractor", "extraction_done": "CSVSaver"}
    )
    
    workflow.add_edge("CSVSaver", "KnowledgeGraph")
    workflow.add_edge("KnowledgeGraph", "FeatureReasoner")
    workflow.add_edge("FeatureReasoner", "ArxivSearcher")
    
    workflow.add_conditional_edges(
        "ArxivSearcher",
        arxiv_router,
        {"loop": "PDFExtractor", "end": END}
    )
    
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


def run_experiment(app, pdf_paths: list = None, thread_id: str = None):
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    
    recursion_limit = Config.MAX_LOOPS * 10 + 50
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}
    initial_state = create_initial_state(pdf_paths=pdf_paths)
    
    run_dir = initial_state.get("run_dir", "unknown")
    run_id = initial_state.get("run_id", thread_id)
    
    import os
    output_path = os.path.join(run_dir, "output.txt")
    tee = TeeWriter(output_path)
    original_stdout = sys.stdout
    sys.stdout = tee
    
    print(f"Feature Mining Agent Started (Run: {run_id})")
    print(f"Output directory: {run_dir}")
    print(f"PDFs to analyze: {len(initial_state['pdf_paths'])}")
    print("\n" + "=" * 60 + "\n")
    
    final_state = None
    try:
        for event in app.stream(initial_state, config):
            for node_name, node_output in event.items():
                print(f"\n[{node_name}] Complete")
                
                if node_name == "PDFExtractor":
                    extracted = len(node_output.get('extracted_data', []))
                    print(f"   Extracted data: {extracted} entries")
                elif node_name == "CSVSaver":
                    csv_path = node_output.get('csv_path', '')
                    print(f"   CSV saved: {csv_path}")
                elif node_name == "KnowledgeGraph":
                    updated = node_output.get('knowledge_graph_updated', False)
                    print(f"   Graph updated: {'success' if updated else 'failed'}")
                elif node_name == "FeatureReasoner":
                    features = node_output.get('proposed_features', [])
                    print(f"   Proposed features: {len(features)}")
                elif node_name == "ArxivSearcher":
                    results = node_output.get('arxiv_results', [])
                    print(f"   Search results: {len(results)} papers")
                
                print()
                final_state = node_output
        
        print("\n" + "=" * 60)
        print("Experiment Complete")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = original_stdout
        tee.close()
        print(f"Log saved: {output_path}")
    
    return final_state


def visualize(app):
    try:
        from IPython.display import Image, display
        display(Image(app.get_graph().draw_mermaid_png()))
    except Exception:
        print("Visualization unavailable (requires IPython environment)")
        print("\nWorkflow structure:")
        print("PDFExtractor -> CSVSaver -> KnowledgeGraph -> FeatureReasoner -> ArxivSearcher")
        print("                                                                  |")
        print("                              <- <- <- <- <- <- <- <- <- <- <- (loop)")
