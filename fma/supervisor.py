"""
Supervisor Agent
Multi-turn conversation agent that orchestrates FMA pipeline
"""

import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Any

from fma.config import FMAConfig
from fma.state import FMAState


SUPERVISOR_SYSTEM_PROMPT = """You are a research supervisor agent for solid electrolyte ionic conductivity analysis.

Based on the user's request, you must decide what action to take:
- "extract": User wants to process papers and extract features
- "analyze": User wants to analyze existing data (correlations, patterns, statistics)
- "respond": You can directly answer the question without running pipelines
- "done": User wants to end the session

Examples:
- "논문 추출해줘" / "새 데이터 처리해줘" → extract
- "상관관계 분석해줘" / "데이터 통계 보여줘" → analyze  
- "안녕" / "고마워" → respond
- "종료" / "끝" → done

Respond in Korean when the user speaks Korean.
Your response format should be:
ACTION: [extract/analyze/respond/done]
RESPONSE: [Your message to the user]
"""


def parse_supervisor_response(response: str) -> tuple:
    """Parse supervisor response to extract action and message."""
    lines = response.strip().split("\n")
    action = "respond"
    message = response
    
    for line in lines:
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip().lower()
        elif line.startswith("RESPONSE:"):
            message = line.replace("RESPONSE:", "").strip()
    
    # Handle multi-line responses
    if "RESPONSE:" in response:
        parts = response.split("RESPONSE:", 1)
        if len(parts) > 1:
            message = parts[1].strip()
    
    # Validate action
    valid_actions = ["extract", "analyze", "respond", "done"]
    if action not in valid_actions:
        action = "respond"
    
    return action, message


def create_supervisor_node():
    """Create the Supervisor node for orchestration."""
    
    llm = ChatOllama(
        model=FMAConfig.MODEL_NAME,
        temperature=0.1
    )
    
    def supervisor_node(state: FMAState) -> dict:
        messages = state.get("messages", [])
        user_request = state.get("user_request", "")
        
        # If returning from pipeline, generate summary response
        analysis_result = state.get("analysis_result", "")
        if analysis_result:
            return {
                "supervisor_response": f"분석이 완료되었습니다.\n\n{analysis_result}",
                "next_action": "respond",
                "analysis_result": "",  # Clear for next round
            }
        
        # Check if extraction just completed
        all_extracted = state.get("all_extracted_data", [])
        if all_extracted and state.get("status") == "extraction_complete":
            return {
                "supervisor_response": f"추출이 완료되었습니다. 총 {len(all_extracted)}개의 데이터를 처리했습니다.",
                "next_action": "respond",
                "status": "running",
            }
        
        if not user_request:
            return {
                "supervisor_response": "무엇을 도와드릴까요? 논문 추출, 데이터 분석 등을 요청할 수 있습니다.",
                "next_action": "respond",
            }
        
        print(f"[Supervisor] Processing request: {user_request}")
        
        # Build message history for LLM
        chat_messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)]
        for msg in messages[-10:]:  # Keep last 10 messages for context
            chat_messages.append(msg)
        chat_messages.append(HumanMessage(content=user_request))
        
        try:
            response = llm.invoke(chat_messages)
            action, message = parse_supervisor_response(response.content)
            
            print(f"[Supervisor] Decided action: {action}")
            
            # Update messages
            new_messages = messages + [
                HumanMessage(content=user_request),
                AIMessage(content=message)
            ]
            
            return {
                "messages": new_messages,
                "supervisor_response": message,
                "next_action": action,
                "user_request": "",  # Clear processed request
            }
        except Exception as e:
            print(f"[Supervisor] Error: {e}")
            return {
                "supervisor_response": f"오류가 발생했습니다: {e}",
                "next_action": "respond",
            }
    
    return supervisor_node


# Legacy function for backward compatibility
def run_supervisor_interactive():
    """Run supervisor in interactive mode (legacy)."""
    from fma.graph import build_fma_workflow, run_interactive_session
    run_interactive_session()


if __name__ == "__main__":
    run_supervisor_interactive()

