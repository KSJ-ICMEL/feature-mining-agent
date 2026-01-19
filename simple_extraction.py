
"""
Simple Extraction Script
Extracts factors affecting ionic conductivity from markdown papers
"""

import os
import sys
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fma.tools.pipeline_tools import get_md_files
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configuration
MODEL_NAME = "gpt-oss:120b"

def read_markdown_file(md_path: str) -> str:
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read {md_path}: {e}")
        return ""

def extract_factors(paper_text: str, filename: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert material scientist analyzing research papers on solid electrolytes.
        
        Your task is to extract the factors that affect ionic conductivity mentioned in the paper, describing specifically HOW they affect it.
        
        Format your response exactly as follows:
        DOI: [Extract DOI if available, otherwise use filename]
        1. [Factor Name]: [Description of how it affects ionic conductivity]
        2. [Factor Name]: [Description of how it affects ionic conductivity]
        ...
        
        Table format response is strictly prohibited.
        Only list the factors with their descriptions. Do not include introductory or concluding text. 
        If no DOI is found in text, look for it in the first few lines or just state "N/A".
        """),
        ("user", """
        Paper content:
        {paper_text}
        
        Extract the factors affecting ionic conductivity.
        """)
    ])
    
    llm = ChatOllama(model=MODEL_NAME, temperature=0.1, top_p=0.5, top_k=50)
    chain = prompt | llm | StrOutputParser()
    
    try:
        # Truncate text if too long to avoid context window issues (simple heuristic)
        # Assuming avg 4 chars per token, 120k tokens is huge, but let's be safe with 50k chars for now if needed, 
        # or just pass it all as these local models usually have descent context.
        # But for speed, let's limit if it's massive.
        return chain.invoke({"paper_text": paper_text[:100000]})
    except Exception as e:
        return f"Error analyzing {filename}: {e}"

def main():
    print("Searching for markdown files...")
    files = get_md_files()
    
    if not files:
        print("No markdown files found.")
        return

    print(f"Found {len(files)} files. Starting extraction (Model: {MODEL_NAME})...\n")
    
    for i, md_path in enumerate(files):
        filename = os.path.basename(md_path)
        print(f"Processing ({i+1}/{len(files)}): {filename}")
        
        content = read_markdown_file(md_path)
        if not content:
            continue
            
        result = extract_factors(content, filename)
        
        print("-" * 40)
        print(result)
        print("-" * 40)
        print("\n")

if __name__ == "__main__":
    main()
