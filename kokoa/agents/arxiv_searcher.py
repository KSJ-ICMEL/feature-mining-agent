"""
arXiv Searcher Node
Search for papers related to proposed features and download PDFs
"""

import os
import urllib.request
from langchain_community.document_loaders import ArxivLoader

from kokoa.config import Config
from kokoa.state import AgentState


def download_arxiv_pdf(arxiv_id: str, save_dir: str) -> str:
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    save_path = os.path.join(save_dir, f"{arxiv_id.replace('/', '_')}.pdf")
    
    try:
        urllib.request.urlretrieve(pdf_url, save_path)
        return save_path
    except Exception as e:
        print(f"      [ERROR] Download failed {arxiv_id}: {e}")
        return ""


def arxiv_searcher_node(state: AgentState) -> dict:
    print("[arXiv Searcher] Searching papers...")
    
    selected_feature = state.get("selected_feature", "")
    arxiv_query = state.get("arxiv_query", "")
    run_dir = state.get("run_dir", ".")
    research_log = state.get("research_log", []).copy()
    pdf_paths = state.get("pdf_paths", []).copy()
    downloaded_pdfs = state.get("downloaded_pdfs", []).copy()
    iteration_count = state.get("iteration_count", 0)
    
    if not selected_feature and not arxiv_query:
        print("   [WARN] No feature to search")
        return {
            "status": "no_search_query",
            "research_log": research_log + ["arXiv Searcher: No query provided"]
        }
    
    search_query = arxiv_query or f"solid electrolyte ionic conductivity {selected_feature}"
    print(f"   [QUERY] {search_query}")
    
    try:
        loader = ArxivLoader(
            query=search_query,
            load_max_docs=Config.ARXIV_MAX_DOCS,
            load_all_available_meta=True
        )
        docs = loader.load()
        
        if not docs:
            print("   [WARN] No relevant papers found")
            return {
                "arxiv_results": [],
                "status": "no_results",
                "iteration_count": iteration_count + 1,
                "research_log": research_log + ["arXiv Searcher: No papers found"]
            }
        
        pdf_dir = os.path.join(run_dir, "pdf")
        os.makedirs(pdf_dir, exist_ok=True)
        
        arxiv_results = []
        new_pdfs = []
        
        for doc in docs:
            entry_id = doc.metadata.get("entry_id", "")
            arxiv_id = entry_id.split("/")[-1] if entry_id else ""
            title = doc.metadata.get("Title", "Unknown")
            
            print(f"   [PAPER] {title[:60]}...")
            
            if arxiv_id:
                pdf_path = download_arxiv_pdf(arxiv_id, pdf_dir)
                if pdf_path:
                    new_pdfs.append(pdf_path)
                    downloaded_pdfs.append(pdf_path)
                    print(f"      [DONE] Downloaded: {os.path.basename(pdf_path)}")
            
            arxiv_results.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "summary": doc.metadata.get("Summary", "")[:200],
                "pdf_path": pdf_path if arxiv_id else ""
            })
        
        pdf_paths.extend(new_pdfs)
        
        print(f"   [DONE] Found {len(docs)} papers, downloaded {len(new_pdfs)} PDFs")
        research_log.append(f"arXiv Searcher: Found {len(docs)} papers, downloaded {len(new_pdfs)} PDFs for '{selected_feature}'")
        
        new_status = "loop_continue" if new_pdfs else "search_complete"
        
        return {
            "arxiv_results": arxiv_results,
            "downloaded_pdfs": downloaded_pdfs,
            "pdf_paths": pdf_paths,
            "current_pdf_index": len(pdf_paths) - len(new_pdfs),
            "status": new_status,
            "iteration_count": iteration_count + 1,
            "research_log": research_log
        }
        
    except Exception as e:
        print(f"   [ERROR] Search failed: {e}")
        research_log.append(f"arXiv Searcher: Error - {str(e)[:100]}")
        return {
            "arxiv_results": [],
            "status": "error",
            "iteration_count": iteration_count + 1,
            "research_log": research_log
        }


def create_arxiv_searcher_node():
    def node_fn(state: AgentState) -> dict:
        return arxiv_searcher_node(state)
    return node_fn
