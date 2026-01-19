"""
Standardizer Agent Node
Unit conversion and vector similarity search for column mapping
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Optional

from fma.config import FMAConfig
from fma.state import FMAState


def get_text_embedding(text: str) -> np.ndarray:
    """
    Mock text embedding function.
    In production, use OpenAI or HuggingFace embeddings.
    """
    np.random.seed(sum(ord(c) for c in text.lower()))
    return np.random.rand(128)


def find_similar_column(
    new_col: str, 
    existing_embeddings: Dict[str, List[float]], 
    threshold: float = None
) -> Tuple[Optional[str], float]:
    if threshold is None:
        threshold = FMAConfig.VECTOR_SIMILARITY_THRESHOLD
    
    if not existing_embeddings:
        return None, 0.0
    
    new_vec = get_text_embedding(new_col).reshape(1, -1)
    
    best_match = None
    best_score = -1.0
    
    for col, emb in existing_embeddings.items():
        curr_vec = np.array(emb).reshape(1, -1)
        score = cosine_similarity(new_vec, curr_vec)[0][0]
        
        if score > best_score:
            best_score = score
            best_match = col
    
    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def standardize_unit(value: float, from_unit: str) -> Tuple[float, str]:
    unit_conversions = {
        ("S/cm", "mS/cm"): lambda x: x * 1000,
        ("mS/cm", "S/cm"): lambda x: x / 1000,
        ("K", "C"): lambda x: x - 273.15,
        ("C", "K"): lambda x: x + 273.15,
    }
    
    return value, from_unit


def standardizer_node(state: FMAState) -> dict:
    print("[Standardizer] Performing unit conversion and vector search...")
    
    all_extracted = state.get("all_extracted_data", [])
    existing_columns = state.get("existing_columns", [])
    research_log = state.get("research_log", []).copy()
    
    if not all_extracted:
        print("   [SKIP] No data to standardize")
        return {"research_log": research_log + ["Standardizer: No data to process"]}
    
    column_embeddings = {col: get_text_embedding(col).tolist() for col in existing_columns}
    
    all_feature_keys = set()
    for entry in all_extracted:
        all_feature_keys.update(entry.get("features", {}).keys())
    
    mapping_suggestions = {}
    new_cols = []
    
    print(f"   Found {len(all_feature_keys)} unique feature keys")
    
    for key in all_feature_keys:
        similar_col, score = find_similar_column(key, column_embeddings)
        
        if similar_col:
            print(f"   Mapping: '{key}' -> '{similar_col}' (score: {score:.3f})")
            mapping_suggestions[key] = similar_col
        else:
            print(f"   New column: '{key}'")
            new_cols.append(key)
    
    standardized_data = {}
    for entry in all_extracted:
        source = entry.get("source_file", "unknown")
        std_entry = {
            "doi": entry.get("doi", ""),
            "material_id": entry.get("material_id", ""),
        }
        
        for key, feat in entry.get("features", {}).items():
            if isinstance(feat, dict):
                value = feat.get("value")
                unit = feat.get("unit", "")
            else:
                value = feat
                unit = ""
            
            target_col = mapping_suggestions.get(key, key)
            std_entry[target_col] = value
        
        standardized_data[source] = std_entry
    
    research_log.append(f"Standardizer: {len(mapping_suggestions)} mapped, {len(new_cols)} new columns")
    
    return {
        "column_embeddings": column_embeddings,
        "standardized_data": standardized_data,
        "column_mapping_suggestions": mapping_suggestions,
        "new_columns_to_add": new_cols,
        "research_log": research_log
    }


def create_standardizer_node():
    def node_fn(state: FMAState) -> dict:
        return standardizer_node(state)
    return node_fn
