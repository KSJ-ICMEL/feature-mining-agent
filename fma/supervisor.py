"""
Supervisor Agent
Multi-turn conversation agent with tool calling for descriptor discovery
"""

import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from typing import TypedDict, List, Any

from fma.config import FMAConfig
from fma.tools.db_tools import query_csv_tool, correlation_tool
from fma.tools.graph_tools import query_graph_tool, find_material_patterns
from fma.tools.pipeline_tools import check_processing_status_tool, run_extraction_tool


SUPERVISOR_SYSTEM_PROMPT = """You are a research supervisor agent for solid electrolyte ionic conductivity analysis.

Your capabilities:
1. Check if all research papers have been processed into the database
2. Run extraction pipeline to process new papers
3. Query the CSV database for quantitative analysis
4. Query the Neo4j knowledge graph for relationship patterns
5. Find correlations between features and ionic conductivity

When the user asks for descriptor discovery:
1. First check processing status
2. If papers are unprocessed, run extraction first
3. Then perform correlation analysis
4. Query the knowledge graph for patterns
5. Synthesize findings and report to user

Always explain your reasoning before taking actions.
Respond in Korean when the user speaks Korean.
"""


class SupervisorState(TypedDict):
    messages: List[Any]
    

def create_supervisor_agent():
    llm = ChatOllama(
        model=FMAConfig.MODEL_NAME,
        temperature=0.1
    )
    
    tools = [
        check_processing_status_tool,
        run_extraction_tool,
        query_csv_tool,
        correlation_tool,
        query_graph_tool,
        find_material_patterns,
    ]
    
    agent = create_react_agent(
        llm,
        tools,
        prompt=SUPERVISOR_SYSTEM_PROMPT,
    )
    
    return agent


def run_supervisor_interactive():
    print("\n" + "=" * 60)
    print("Feature Mining Agent - Interactive Mode")
    print("=" * 60)
    print("Supervisor Agent가 활성화되었습니다.")
    print("질문을 입력하세요. 종료하려면 'exit' 또는 'quit'을 입력하세요.\n")
    
    agent = create_supervisor_agent()
    memory = MemorySaver()
    
    config = {"configurable": {"thread_id": "supervisor-session"}}
    messages = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n세션을 종료합니다.")
                break
            
            messages.append(HumanMessage(content=user_input))
            
            print("\nSupervisor: ", end="", flush=True)
            
            response = agent.invoke(
                {"messages": messages},
                config
            )
            
            ai_message = response["messages"][-1]
            messages.append(ai_message)
            
            print(ai_message.content)
            print()
            
        except KeyboardInterrupt:
            print("\n\n세션을 종료합니다.")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_supervisor_interactive()
