"""
Analyzer Agent
Performs data analysis using CSV and Neo4j knowledge graph
"""

import os
import pandas as pd
from scipy import stats
from neo4j import GraphDatabase
from dotenv import load_dotenv

from fma.state import FMAState
from fma.config import FMAConfig

load_dotenv()


def get_latest_csv_path() -> str:
    runs_dir = FMAConfig.RUNS_DIR
    if not os.path.exists(runs_dir):
        return ""
    
    run_folders = [f for f in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, f))]
    if not run_folders:
        return ""
    
    latest_run = sorted(run_folders)[-1]
    csv_path = os.path.join(runs_dir, latest_run, "extracted_features.csv")
    
    if os.path.exists(csv_path):
        return csv_path
    return ""


def analyze_correlations(target_column: str = "ionic_cond") -> str:
    """Analyze correlations between features and target column."""
    csv_path = get_latest_csv_path()
    if not csv_path:
        return "No CSV data found. Run extraction pipeline first."
    
    try:
        df = pd.read_csv(csv_path)
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if target_column not in numeric_cols:
            return f"Target column '{target_column}' not found. Available: {numeric_cols}"
        
        correlations = {}
        for col in numeric_cols:
            if col != target_column:
                valid_mask = df[col].notna() & df[target_column].notna()
                if valid_mask.sum() >= 3:
                    corr, p_value = stats.pearsonr(
                        df.loc[valid_mask, col],
                        df.loc[valid_mask, target_column]
                    )
                    correlations[col] = {"correlation": corr, "p_value": p_value}
        
        if not correlations:
            return "Not enough data for correlation analysis."
        
        sorted_corrs = sorted(correlations.items(), key=lambda x: abs(x[1]["correlation"]), reverse=True)
        
        result = f"Correlation analysis with '{target_column}':\n\n"
        result += "| Feature | Correlation | P-value | Significance |\n"
        result += "|---------|-------------|---------|---------------|\n"
        
        for feat, vals in sorted_corrs:
            sig = "***" if vals["p_value"] < 0.001 else "**" if vals["p_value"] < 0.01 else "*" if vals["p_value"] < 0.05 else ""
            result += f"| {feat} | {vals['correlation']:.4f} | {vals['p_value']:.4f} | {sig} |\n"
        
        return result
    except Exception as e:
        return f"Error in correlation analysis: {e}"


def get_data_summary() -> str:
    """Get summary of extracted data."""
    csv_path = get_latest_csv_path()
    if not csv_path:
        return "No CSV data found. Run extraction pipeline first."
    
    try:
        df = pd.read_csv(csv_path)
        result = f"Data Summary:\n"
        result += f"- Total records: {len(df)}\n"
        result += f"- Columns: {list(df.columns)}\n\n"
        result += f"Statistics:\n{df.describe().to_string()}"
        return result
    except Exception as e:
        return f"Error reading CSV: {e}"


def query_neo4j_patterns(property_type: str = "ionic_cond") -> str:
    """Find material patterns from Neo4j knowledge graph."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not all([uri, username, password]):
        return "Neo4j credentials not configured. Skipping graph analysis."
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        
        query = """
        MATCH (m:Material)-[:HAS_PROPERTY]->(p:Property {type: $prop_type})
        OPTIONAL MATCH (m)-[:PROCESSED_BY]->(proc:Process)
        RETURN m.formula as material, p.value as value, p.unit as unit,
               collect(DISTINCT {type: proc.type, value: proc.value}) as processes
        ORDER BY p.value DESC
        LIMIT 10
        """
        
        with driver.session() as session:
            results = [dict(record) for record in session.run(query, {"prop_type": property_type})]
        
        driver.close()
        
        if not results:
            return f"No materials found with property '{property_type}'."
        
        output = f"Top 10 materials by {property_type}:\n\n"
        output += "| Material | Value | Processes |\n"
        output += "|----------|-------|----------|\n"
        
        for r in results:
            procs = ", ".join([f"{p['type']}={p['value']}" for p in r['processes'] if p['type']])
            output += f"| {r['material']} | {r['value']} {r['unit'] or ''} | {procs} |\n"
        
        return output
    except Exception as e:
        return f"Neo4j query error: {e}"


def create_analyzer_node():
    """Create the Analyzer node for data analysis."""
    
    def analyzer_node(state: FMAState) -> dict:
        print("[Analyzer] Running data analysis...")
        
        user_request = state.get("user_request", "").lower()
        results = []
        
        # Determine analysis type from request
        if "상관" in user_request or "correlation" in user_request:
            results.append(analyze_correlations())
        elif "요약" in user_request or "summary" in user_request or "통계" in user_request:
            results.append(get_data_summary())
        elif "패턴" in user_request or "pattern" in user_request:
            results.append(query_neo4j_patterns())
        else:
            # Default: run all analyses
            results.append(get_data_summary())
            results.append(analyze_correlations())
            results.append(query_neo4j_patterns())
        
        analysis_result = "\n\n---\n\n".join(results)
        
        print(f"[Analyzer] Analysis complete.")
        
        return {
            "analysis_result": analysis_result,
            "next_action": "respond",
            "research_log": state.get("research_log", []) + ["[Analyzer] Data analysis completed"]
        }
    
    return analyzer_node
