"""
Knowledge Graph Node
Store manipulated variable and ionic conductivity relationships in Neo4J
"""

import json
from neo4j import GraphDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from kokoa.config import Config
from kokoa.state import AgentState


ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert in analyzing solid electrolyte research data.

Analyze the given experimental data and determine the effect of each manipulated variable on ionic conductivity.

Respond in JSON format:
{{
    "relationships": [
        {{
            "variable": "Variable name",
            "value_change": "Increase/decrease/change content",
            "effect": "INCREASES or DECREASES",
            "confidence": "high/medium/low"
        }}
    ]
}}"""),
    ("user", """Experimental data:
{experiment_data}

Analyze the relationship between manipulated variables and ionic conductivity from the above data.""")
])


class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def create_relationship(self, variable: str, effect: str, composition: str, conductivity: float):
        with self.driver.session(database=Config.NEO4J_DATABASE) as session:
            session.run("""
                MERGE (v:Variable {name: $variable})
                MERGE (c:Composition {formula: $composition})
                MERGE (v)-[r:AFFECTS {effect: $effect, conductivity: $conductivity}]->(c)
            """, variable=variable, effect=effect, composition=composition, conductivity=conductivity)
    
    def create_effect_relationship(self, variable: str, effect: str, confidence: str):
        with self.driver.session(database=Config.NEO4J_DATABASE) as session:
            session.run("""
                MERGE (v:Variable {name: $variable})
                MERGE (e:Effect {type: $effect})
                MERGE (v)-[r:CAUSES {confidence: $confidence}]->(e)
            """, variable=variable, effect=effect, confidence=confidence)
    
    def get_all_relationships(self):
        with self.driver.session(database=Config.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (v:Variable)-[r:CAUSES]->(e:Effect)
                RETURN v.name as variable, e.type as effect, r.confidence as confidence
            """)
            return [record.data() for record in result]


def knowledge_graph_node(state: AgentState) -> dict:
    print("[Knowledge Graph] Updating knowledge graph...")
    
    extracted_data = state.get("extracted_data", [])
    research_log = state.get("research_log", []).copy()
    
    if not extracted_data:
        print("   [WARN] No data to analyze")
        return {
            "knowledge_graph_updated": False,
            "research_log": research_log + ["Knowledge Graph: No data to analyze"]
        }
    
    llm = ChatOllama(
        model=Config.MODEL_NAME,
        temperature=0.1
    )
    
    data_str = "\n".join([
        f"Composition: {d['composition']}, Ionic conductivity: {d['ionic_conductivity']} S/cm, "
        f"Features: {d['features']}"
        for d in extracted_data
    ])
    
    try:
        print("   [LLM] Analyzing relationships...")
        response = llm.invoke(ANALYSIS_PROMPT.format_messages(experiment_data=data_str))
        
        content = response.content
        content = content.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(content)
        
        print("   [Neo4J] Connecting...")
        neo4j = Neo4jConnection()
        
        for rel in analysis.get("relationships", []):
            variable = rel.get("variable", "")
            effect = rel.get("effect", "UNKNOWN")
            confidence = rel.get("confidence", "low")
            
            neo4j.create_effect_relationship(variable, effect, confidence)
            print(f"      {variable} -> {effect} (confidence: {confidence})")
        
        neo4j.close()
        
        rel_count = len(analysis.get("relationships", []))
        print(f"   [DONE] Saved {rel_count} relationships")
        research_log.append(f"Knowledge Graph: Created {rel_count} relationships")
        
        return {
            "knowledge_graph_updated": True,
            "research_log": research_log
        }
        
    except Exception as e:
        print(f"   [ERROR] Graph update failed: {e}")
        research_log.append(f"Knowledge Graph: Error - {str(e)[:100]}")
        return {
            "knowledge_graph_updated": False,
            "research_log": research_log
        }


def create_knowledge_graph_node():
    def node_fn(state: AgentState) -> dict:
        return knowledge_graph_node(state)
    return node_fn
