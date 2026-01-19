"""
Graph Updater Agent Node
Saves extracted data to Neo4j Knowledge Graph
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

from fma.state import FMAState

load_dotenv()


class Neo4jConnection:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.username = os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
    
    def connect(self):
        if not all([self.uri, self.username, self.password]):
            print("   [WARN] Neo4j credentials not found in .env")
            return False
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"   [ERROR] Neo4j connection failed: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)


def create_material_node(tx, material_id, doi, source_file):
    query = """
    MERGE (m:Material {formula: $formula})
    MERGE (p:Paper {doi: $doi, source_file: $source_file})
    MERGE (m)-[:STUDIED_IN]->(p)
    RETURN m, p
    """
    return tx.run(query, formula=material_id, doi=doi, source_file=source_file)


def create_property_node(tx, material_id, prop_type, value, unit):
    query = """
    MATCH (m:Material {formula: $formula})
    MERGE (prop:Property {type: $prop_type, value: $value, unit: $unit})
    MERGE (m)-[:HAS_PROPERTY]->(prop)
    RETURN prop
    """
    return tx.run(query, formula=material_id, prop_type=prop_type, value=value, unit=unit)


def create_process_node(tx, material_id, process_type, value, unit):
    query = """
    MATCH (m:Material {formula: $formula})
    MERGE (proc:Process {type: $process_type, value: $value, unit: $unit})
    MERGE (m)-[:PROCESSED_BY]->(proc)
    RETURN proc
    """
    return tx.run(query, formula=material_id, process_type=process_type, value=value, unit=unit)


PROPERTY_TYPES = {"ionic_cond", "act_energy", "grain_size", "relative_density"}
PROCESS_TYPES = {"sintering_T", "milling_spd"}


def graph_updater_node(state: FMAState) -> dict:
    print("[Graph Updater] Saving to Neo4j Knowledge Graph...")
    
    research_log = state.get("research_log", []).copy()
    all_extracted = state.get("all_extracted_data", [])
    
    if not all_extracted:
        print("   [SKIP] No data to save")
        return {"research_log": research_log + ["Graph Updater: No data"]}
    
    neo4j = Neo4jConnection()
    if not neo4j.connect():
        return {"research_log": research_log + ["Graph Updater: Connection failed"]}
    
    try:
        with neo4j.driver.session() as session:
            node_count = 0
            
            for entry in all_extracted:
                material_id = entry.get("material_id", "")
                if not material_id:
                    continue
                
                doi = entry.get("doi", "")
                source_file = entry.get("source_file", "")
                
                session.execute_write(create_material_node, material_id, doi, source_file)
                node_count += 1
                
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
                        session.execute_write(create_property_node, material_id, feat_key, value, unit)
                    elif feat_key in PROCESS_TYPES:
                        session.execute_write(create_process_node, material_id, feat_key, value, unit)
                    else:
                        session.execute_write(create_property_node, material_id, feat_key, value, unit)
            
            print(f"   [DONE] Created/updated {node_count} material nodes")
            research_log.append(f"Graph Updater: {node_count} materials saved to Neo4j")
    
    except Exception as e:
        print(f"   [ERROR] Graph update failed: {e}")
        research_log.append(f"Graph Updater: Error - {str(e)[:100]}")
    finally:
        neo4j.close()
    
    return {"research_log": research_log}


def create_graph_updater_node():
    def node_fn(state: FMAState) -> dict:
        return graph_updater_node(state)
    return node_fn
