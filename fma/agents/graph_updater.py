"""
Graph Updater Agent Node
Saves extracted data to Neo4j Knowledge Graph using LangChain Neo4j integration
"""

import os
from dotenv import load_dotenv

from langchain_neo4j import Neo4jGraph

from fma.state import FMAState

load_dotenv()


# Cypher query templates
MERGE_MATERIAL_QUERY = """
MERGE (m:Material {formula: $formula})
MERGE (p:Paper {doi: $doi, source_file: $source_file})
MERGE (m)-[:STUDIED_IN]->(p)
RETURN m, p
"""

MERGE_PROPERTY_QUERY = """
MATCH (m:Material {formula: $formula})
MERGE (prop:Property {type: $prop_type, value: $value, unit: $unit})
MERGE (m)-[:HAS_PROPERTY]->(prop)
RETURN prop
"""

MERGE_PROCESS_QUERY = """
MATCH (m:Material {formula: $formula})
MERGE (proc:Process {type: $process_type, value: $value, unit: $unit})
MERGE (m)-[:PROCESSED_BY]->(proc)
RETURN proc
"""


PROPERTY_TYPES = {"ionic_cond", "act_energy", "grain_size", "relative_density"}
PROCESS_TYPES = {"sintering_T", "milling_spd"}


def get_neo4j_graph() -> Neo4jGraph | None:
    """Create Neo4jGraph connection using environment variables."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not all([uri, username, password]):
        print("   [WARN] Neo4j credentials not found in .env")
        return None
    
    try:
        graph = Neo4jGraph(
            url=uri,
            username=username,
            password=password
        )
        return graph
    except Exception as e:
        print(f"   [ERROR] Neo4j connection failed: {e}")
        return None


def graph_updater_node(state: FMAState) -> dict:
    """Main graph updater node function."""
    print("[Graph Updater] Saving to Neo4j Knowledge Graph...")
    
    research_log = state.get("research_log", []).copy()
    all_extracted = state.get("all_extracted_data", [])
    
    if not all_extracted:
        print("   [SKIP] No data to save")
        return {"research_log": research_log + ["Graph Updater: No data"]}
    
    graph = get_neo4j_graph()
    if graph is None:
        return {"research_log": research_log + ["Graph Updater: Connection failed"]}
    
    try:
        node_count = 0
        
        for entry in all_extracted:
            material_id = entry.get("material_id", "")
            if not material_id:
                continue
            
            doi = entry.get("doi", "")
            source_file = entry.get("source_file", "")
            
            # Create material and paper nodes
            graph.query(
                MERGE_MATERIAL_QUERY,
                params={"formula": material_id, "doi": doi, "source_file": source_file}
            )
            node_count += 1
            
            # Create property/process nodes
            for feat_key, feat_data in entry.get("features", {}).items():
                if isinstance(feat_data, dict):
                    value = feat_data.get("value")
                    unit = feat_data.get("unit", "")
                else:
                    value = feat_data
                    unit = ""
                
                if value is None:
                    continue
                
                if feat_key in PROPERTY_TYPES:
                    graph.query(
                        MERGE_PROPERTY_QUERY,
                        params={"formula": material_id, "prop_type": feat_key, "value": value, "unit": unit}
                    )
                elif feat_key in PROCESS_TYPES:
                    graph.query(
                        MERGE_PROCESS_QUERY,
                        params={"formula": material_id, "process_type": feat_key, "value": value, "unit": unit}
                    )
                else:
                    # Default to property for unknown types
                    graph.query(
                        MERGE_PROPERTY_QUERY,
                        params={"formula": material_id, "prop_type": feat_key, "value": value, "unit": unit}
                    )
        
        print(f"   [DONE] Created/updated {node_count} material nodes")
        research_log.append(f"Graph Updater: {node_count} materials saved to Neo4j")
    
    except Exception as e:
        print(f"   [ERROR] Graph update failed: {e}")
        research_log.append(f"Graph Updater: Error - {str(e)[:100]}")
    
    return {"research_log": research_log}


def create_graph_updater_node():
    """Factory function for LangGraph node."""
    def node_fn(state: FMAState) -> dict:
        return graph_updater_node(state)
    return node_fn
