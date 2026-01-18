"""
Feature Reasoner Node
Analyze knowledge graph and propose new features using advanced reasoning
"""

import json
from neo4j import GraphDatabase
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from kokoa.config import Config
from kokoa.state import AgentState


REASONING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert in proposing new research directions for improving solid electrolyte ionic conductivity.

Analyze the given knowledge graph data to:
1. Identify patterns in the known manipulated variables
2. Propose new features (manipulated variables) that have not been explored
3. Provide scientific rationale for your proposals

Respond in JSON format:
{{
    "analysis": "Summary of current knowledge graph analysis",
    "proposed_features": [
        {{
            "name": "New feature name",
            "rationale": "Proposal rationale",
            "expected_effect": "Expected ionic conductivity change",
            "search_query": "Query to use for arXiv search"
        }}
    ],
    "priority_feature": "Feature to explore first"
}}"""),
    ("user", """Current knowledge graph relationships:
{graph_data}

Based on the analyzed manipulated variables, propose new features worth investigating for improving solid electrolyte ionic conductivity.""")
])


class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def get_all_relationships(self):
        with self.driver.session(database=Config.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (v:Variable)-[r]->(e)
                RETURN v.name as variable, type(r) as relationship, 
                       labels(e)[0] as target_type, properties(e) as target_props
            """)
            return [record.data() for record in result]


def feature_reasoner_node(state: AgentState) -> dict:
    print("[Feature Reasoner] Starting advanced reasoning...")
    
    research_log = state.get("research_log", []).copy()
    
    try:
        print("   [Neo4J] Loading graph data...")
        neo4j = Neo4jConnection()
        relationships = neo4j.get_all_relationships()
        neo4j.close()
        
        if not relationships:
            print("   [WARN] Knowledge graph is empty")
            return {
                "proposed_features": [],
                "research_log": research_log + ["Feature Reasoner: Empty knowledge graph"]
            }
        
        graph_str = "\n".join([
            f"- {r['variable']} --[{r['relationship']}]--> {r['target_type']}: {r['target_props']}"
            for r in relationships
        ])
        
        llm = ChatOllama(
            model=Config.MODEL_NAME,
            temperature=0.3,
            extra_body={"reasoning_effort": "high"}
        )
        
        print("   [LLM] Reasoning (reasoning_effort: high)...")
        response = llm.invoke(REASONING_PROMPT.format_messages(graph_data=graph_str))
        
        content = response.content
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        
        proposed = result.get("proposed_features", [])
        priority = result.get("priority_feature", "")
        
        print(f"   [DONE] Proposed {len(proposed)} new features")
        print(f"   [PRIORITY] {priority}")
        
        for feat in proposed:
            print(f"      - {feat['name']}: {feat['rationale'][:50]}...")
        
        research_log.append(f"Feature Reasoner: Proposed {len(proposed)} features, priority: {priority}")
        
        return {
            "proposed_features": [f["name"] for f in proposed],
            "selected_feature": priority,
            "arxiv_query": proposed[0]["search_query"] if proposed else "",
            "research_log": research_log
        }
        
    except Exception as e:
        print(f"   [ERROR] Reasoning failed: {e}")
        research_log.append(f"Feature Reasoner: Error - {str(e)[:100]}")
        return {
            "proposed_features": [],
            "research_log": research_log
        }


def create_feature_reasoner_node():
    def node_fn(state: AgentState) -> dict:
        return feature_reasoner_node(state)
    return node_fn
