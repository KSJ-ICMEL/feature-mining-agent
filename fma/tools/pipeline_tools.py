"""
Pipeline Tools for Supervisor Agent
Check processing status and trigger extraction
"""

import os
from langchain_core.tools import tool

from fma.config import FMAConfig


def get_md_files() -> list:
    md_dir = FMAConfig.MD_DIRECTORY
    if not os.path.exists(md_dir):
        return []
    return [f for f in os.listdir(md_dir) if f.lower().endswith('.md')]


def get_processed_files() -> list:
    runs_dir = FMAConfig.RUNS_DIR
    if not os.path.exists(runs_dir):
        return []
    
    run_folders = sorted([f for f in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, f))])
    if not run_folders:
        return []
    
    import csv
    latest_run = run_folders[-1]
    csv_path = os.path.join(runs_dir, latest_run, "extracted_features.csv")
    
    if not os.path.exists(csv_path):
        return []
    
    processed = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                source = row.get('source_file', '')
                if source:
                    processed.append(source)
    except Exception:
        pass
    
    return processed


@tool
def check_processing_status_tool() -> str:
    """
    Check how many markdown papers have been processed into the database.
    Use this to determine if extraction is needed before analysis.
    
    Returns:
        Status report of processed vs unprocessed papers
    """
    md_files = get_md_files()
    processed = get_processed_files()
    
    unprocessed = [f for f in md_files if f not in processed]
    
    report = f"Processing Status:\n"
    report += f"  - Total markdown files: {len(md_files)}\n"
    report += f"  - Already processed: {len(processed)}\n"
    report += f"  - Unprocessed: {len(unprocessed)}\n"
    
    if unprocessed:
        report += f"\nUnprocessed files:\n"
        for f in unprocessed[:10]:
            report += f"  - {f}\n"
        if len(unprocessed) > 10:
            report += f"  ... and {len(unprocessed) - 10} more\n"
    
    return report


@tool
def run_extraction_tool() -> str:
    """
    Run the extraction pipeline on all unprocessed markdown files.
    This will extract features, save to CSV, and update the Neo4j knowledge graph.
    
    Returns:
        Extraction result summary
    """
    from fma.graph import build_fma_workflow, run_fma_pipeline
    
    md_files = get_md_files()
    processed = get_processed_files()
    unprocessed = [f for f in md_files if f not in processed]
    
    if not unprocessed:
        return "All papers are already processed. No extraction needed."
    
    md_dir = FMAConfig.MD_DIRECTORY
    md_paths = [os.path.join(md_dir, f) for f in unprocessed]
    
    try:
        app = build_fma_workflow()
        result = run_fma_pipeline(app, md_paths=md_paths, auto_approve=True)
        
        if result:
            return f"Extraction complete. Processed {len(md_paths)} new papers."
        return "Extraction completed but no results returned."
    except Exception as e:
        return f"Extraction failed: {e}"
