"""
Database Tools for Supervisor Agent
CSV querying and statistical analysis
"""

import os
import pandas as pd
from scipy import stats
from langchain_core.tools import tool

from fma.config import FMAConfig


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


@tool
def query_csv_tool(query: str) -> str:
    """
    Query the extracted features CSV using pandas.
    Use this to get statistics, filter data, or aggregate values.
    
    Args:
        query: A description of what data you want, e.g., "show all materials with ionic_cond > 1e-3"
    
    Returns:
        Query results as formatted string
    """
    csv_path = get_latest_csv_path()
    if not csv_path:
        return "No CSV data found. Run extraction pipeline first."
    
    try:
        df = pd.read_csv(csv_path)
        
        result = f"CSV loaded: {len(df)} rows, columns: {list(df.columns)}\n\n"
        result += f"Sample data:\n{df.head().to_string()}\n\n"
        result += f"Summary statistics:\n{df.describe().to_string()}"
        
        return result
    except Exception as e:
        return f"Error reading CSV: {e}"


@tool
def correlation_tool(target_column: str = "ionic_cond") -> str:
    """
    Calculate correlation coefficients between all numeric columns and the target column.
    Use this to find features that correlate with ionic conductivity.
    
    Args:
        target_column: The target variable to correlate against (default: ionic_cond)
    
    Returns:
        Correlation analysis results
    """
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
