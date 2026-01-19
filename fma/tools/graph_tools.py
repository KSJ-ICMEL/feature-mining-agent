"""
Graph Tools for Supervisor Agent
Neo4j querying for relationship patterns
"""

import os
from neo4j import GraphDatabase
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()


class Neo4jConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.username = os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
    
    def connect(self):
        if self.driver:
            return True
        if not all([self.uri, self.username, self.password]):
            return False
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False
    
    def run_query(self, query, parameters=None):
        if not self.connect():
            return []
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]


@tool
def query_graph_tool(cypher_query: str) -> str:
    """
    Execute a Cypher query on the Neo4j knowledge graph.
    Use this to explore relationships between materials, properties, and processes.
    
    Common patterns:
    - Find all materials: MATCH (m:Material) RETURN m.formula
    - Find high conductivity materials: MATCH (m:Material)-[:HAS_PROPERTY]->(p:Property {type: 'ionic_cond'}) WHERE p.value > 1e-3 RETURN m.formula, p.value
    - Find process patterns: MATCH (m:Material)-[:PROCESSED_BY]->(proc:Process) RETURN m.formula, proc.type, proc.value
    
    Args:
        cypher_query: Cypher query to execute
    
    Returns:
        Query results as formatted string
    """
    neo4j = Neo4jConnection.get_instance()
    
    if not neo4j.connect():
        return "Neo4j connection failed. Check credentials in .env file."
    
    try:
        results = neo4j.run_query(cypher_query)
        
        if not results:
            return "Query returned no results."
        
        output = f"Found {len(results)} results:\n\n"
        for i, record in enumerate(results[:20], 1):
            output += f"{i}. {record}\n"
        
        if len(results) > 20:
            output += f"\n... and {len(results) - 20} more results."
        
        return output
    except Exception as e:
        return f"Query error: {e}"


@tool
def find_material_patterns(property_type: str = "ionic_cond") -> str:
    """
    Find patterns in materials that have high values for a specific property.
    Analyzes common processes and characteristics of high-performing materials.
    
    Args:
        property_type: Property to analyze (default: ionic_cond)
    
    Returns:
        Pattern analysis results
    """
    neo4j = Neo4jConnection.get_instance()
    
    if not neo4j.connect():
        return "Neo4j connection failed."
    
    try:
        query = """
        MATCH (m:Material)-[:HAS_PROPERTY]->(p:Property {type: $prop_type})
        OPTIONAL MATCH (m)-[:PROCESSED_BY]->(proc:Process)
        RETURN m.formula as material, p.value as value, p.unit as unit,
               collect(DISTINCT {type: proc.type, value: proc.value}) as processes
        ORDER BY p.value DESC
        LIMIT 10
        """
        
        results = neo4j.run_query(query, {"prop_type": property_type})
        
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
        return f"Pattern analysis error: {e}"
