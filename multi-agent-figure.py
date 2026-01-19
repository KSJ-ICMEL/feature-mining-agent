
"""
Multi-Agent Figure Generator
Generates a PNG image of the FMA LangGraph workflow
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fma.graph import build_fma_workflow

def generate_graph_image():
    print("Building FMA workflow...")
    app = build_fma_workflow()
    
    output_file = "fma_graph.png"
    print(f"Generating graph image: {output_file}")
    
    try:
        # Get the graph and draw as mermaid PNG
        graph_png = app.get_graph().draw_mermaid_png()
        
        with open(output_file, "wb") as f:
            f.write(graph_png)
            
        print(f"Successfully saved {output_file}")
        
    except Exception as e:
        print(f"Failed to generate graph image: {e}")
        print("\nPossible fix: Ensure 'langgraph' and 'graphviz' dependencies are installed.")

if __name__ == "__main__":
    generate_graph_image()
