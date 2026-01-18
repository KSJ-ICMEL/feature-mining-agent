#!/usr/bin/env python
"""
Feature Mining Agent
====================
LangGraph-based agent for solid electrolyte ionic conductivity research

Usage:
    python main.py                          # Analyze PDFs in initial_state/pdf
    python main.py --pdf-dir /path/to/pdfs  # Analyze PDFs in specific directory
    python main.py --visualize              # Visualize workflow
"""

import argparse
import os

from kokoa.graph import build_workflow, run_experiment, visualize


def main():
    parser = argparse.ArgumentParser(description="Feature Mining Agent")
    parser.add_argument("--pdf-dir", type=str, help="Directory containing PDF files")
    parser.add_argument("--visualize", action="store_true", help="Visualize workflow")
    args = parser.parse_args()
    
    print("Initializing Feature Mining Agent...")
    
    app = build_workflow()
    print("   Workflow build complete")
    
    if args.visualize:
        visualize(app)
        return
    
    pdf_paths = None
    if args.pdf_dir:
        if os.path.isdir(args.pdf_dir):
            pdf_paths = [
                os.path.join(args.pdf_dir, f) 
                for f in os.listdir(args.pdf_dir) 
                if f.lower().endswith('.pdf')
            ]
            print(f"   Found {len(pdf_paths)} PDF files")
        else:
            print(f"   [ERROR] Directory not found: {args.pdf_dir}")
            return
    
    run_experiment(app, pdf_paths=pdf_paths)


if __name__ == "__main__":
    main()
