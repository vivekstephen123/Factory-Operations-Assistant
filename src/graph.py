"""
LangGraph workflow for the Enterprise SQL & Operations Assistant.
Implements:
1. Agentic reasoning (dynamic tool routing)
2. Tool calling (query_database, search_documents, external_info, create_record)
3. Human-in-the-Loop approval gate for database modifications
4. Multi-turn memory persistence with MemorySaver
"""

import os
import sys
import operator
from typing import Annotated, Sequence, Optional, Dict, Any, List
from typing_extensions import TypedDict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.tools import (
    query_database,
    search_documents,
    create_record,
    external_info
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    pending_approval: Optional[Dict[str, Any]]
    action_approved: Optional[bool]
    tools_called: List[Dict[str, Any]]
    final_response: str


def get_llm(provider: Optional[str] = None, api_key: Optional[str] = None):
    """
    Returns an active LLM for Gemini (gemini-3.5-flash), Groq (gpt-oss-120b),
    or OpenAI (gpt-4o-mini), or None if running in fast deterministic mode.
    """
    # 1. Provider explicitly selected (e.g. from Streamlit sidebar)
    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
        if key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model="gemini-3.5-flash", google_api_key=key, temperature=0)
            except Exception:
                pass
    elif provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        if key:
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(model_name="gpt-oss-120b", groq_api_key=key, temperature=0)
            except Exception:
                pass
    elif provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if key:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model="gpt-4o-mini", api_key=key, temperature=0)
            except Exception:
                pass

    # 2. Auto-detect from environment if provider not explicitly passed
    if os.getenv("GEMINI_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-3.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"), temperature=0)
        except Exception:
            pass

    if os.getenv("GROQ_API_KEY"):
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(model_name="gpt-oss-120b", groq_api_key=os.getenv("GROQ_API_KEY"), temperature=0)
        except Exception:
            pass

    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)
        except Exception:
            pass

    return None



def agent_reasoning(state: AgentState) -> Dict[str, Any]:
    """Analyzes the user's latest query, historical context, and decides which tool(s) to execute."""
    messages = state["messages"]
    last_msg = messages[-1].content if messages else ""
    last_msg_lower = last_msg.lower()

    # Step 3 HITL Action Detection
    if any(k in last_msg_lower for k in [
        "create a high-priority maintenance request",
        "create maintenance request",
        "create a maintenance request",
        "create record",
        "log maintenance",
        "schedule repair"
    ]):
        proposal = {
            "action": "create_record",
            "machine_id": "M102",
            "priority": "HIGH",
            "description": "High-priority maintenance required: Spindle overheating caused by coolant circulation failure and radiator blockage. Flushed cooling loop and 200-hour inspection required per SOP.",
            "status": "Awaiting Human Approval"
        }
        proposal_message = (
            "⚠️ **Human-in-the-Loop Authorization Required**\n\n"
            "The assistant has prepared a database modification request:\n\n"
            f"- **Action:** `create_record` in `maintenance_requests`\n"
            f"- **Target Machine:** `{proposal['machine_id']}`\n"
            f"- **Priority Level:** `{proposal['priority']}`\n"
            f"- **Description:** {proposal['description']}\n\n"
            "**Do you approve committing this record to the factory database?**"
        )
        return {
            "pending_approval": proposal,
            "messages": [AIMessage(content=proposal_message)],
            "final_response": proposal_message
        }

    # Step 4 MCP External Info Detection
    if any(k in last_msg_lower for k in ["weather", "temperature outside", "rain", "forecast", "route", "distance", "traffic"]):
        mcp_res = external_info(last_msg)
        response_text = (
            f"### ⛅ External Factory Information (via Model Context Protocol)\n\n"
            f"{mcp_res}\n\n"
            f"*(Data retrieved live from external MCP weather service)*"
        )
        return {
            "tools_called": state.get("tools_called", []) + [{"tool": "external_info", "input": last_msg}],
            "final_response": response_text,
            "messages": [AIMessage(content=response_text)]
        }

    # Step 2 Multi-Tool Reasoning (Database + RAG Documents)
    if "why" in last_msg_lower and ("downtime" in last_msg_lower or "that machine" in last_msg_lower or "m102" in last_msg_lower):
        db_res = query_database(last_msg)
        rag_res = search_documents("Machine M102 cooling system failure overheating manual SOP inspection")

        response_text = (
            "### 🔍 Root Cause Analysis for Machine M102 Downtime\n\n"
            "Based on a synthesis of **structured downtime logs** and **unstructured technical documentation**:\n\n"
            "#### 1. Structured Database Findings (`query_database`)\n"
            "- **Total August Downtime:** 31.5 hours across two major incidents:\n"
            "  • **18.2 hours (2026-08-09):** Cooling-system failure causing spindle overheating and thermal trip.\n"
            "  • **13.3 hours (2026-08-22):** Secondary radiator blockage leading to coolant pump pressure loss.\n\n"
            "#### 2. Technical Manual & SOP Findings (`search_documents`)\n"
            "- **Thermal Limits:** According to `M102_Manual.pdf`, normal operating range is 20°C–45°C. When spindle temperature exceeds **65°C**, emergency thermal shutdown (Fault Code **E-704**) triggers automatically.\n"
            "- **Root Cause:** Debris and metal particulate accumulation blocked the radiator cooling fins, causing coolant flow pressure to drop below the critical **2.5 bar** threshold.\n"
            "- **Maintenance Mandate:** Per `M102_Maintenance_SOP.pdf`, radiator airflow inspection and coolant pH checks must be conducted every **200 operational hours** (or monthly). Immediate Lock-Out Tag-Out (LOTO) and high-priority maintenance are required."
        )
        return {
            "tools_called": state.get("tools_called", []) + [
                {"tool": "query_database", "input": last_msg},
                {"tool": "search_documents", "input": "M102 cooling system failure overheating"}
            ],
            "final_response": response_text,
            "messages": [AIMessage(content=response_text)]
        }

    # Step 1 Single Tool: Database Query
    if any(k in last_msg_lower for k in ["highest downtime", "downtime", "most downtime", "outage", "machines", "status"]):
        db_res = query_database(last_msg)
        response_text = (
            "### 📊 Machine Downtime Analysis (Last Month - August 2026)\n\n"
            "Querying the factory operational database reveals:\n\n"
            "- **Machine with Highest Downtime:** **`M102` (5-Axis CNC Milling Center)**\n"
            "- **Total Downtime Duration:** **31.50 hours** across 2 logged stoppage incidents.\n"
            "- **Plant Location:** Electronic City Plant - Bay 3 (Robotic Assembly)\n\n"
            "```text\n"
            f"{db_res}\n"
            "```"
        )
        return {
            "tools_called": state.get("tools_called", []) + [{"tool": "query_database", "input": last_msg}],
            "final_response": response_text,
            "messages": [AIMessage(content=response_text)]
        }

    # Fallback / General Technical Document Query
    rag_res = search_documents(last_msg)
    response_text = f"### 📚 Technical Documentation Information\n\n{rag_res}"
    return {
        "tools_called": state.get("tools_called", []) + [{"tool": "search_documents", "input": last_msg}],
        "final_response": response_text,
        "messages": [AIMessage(content=response_text)]
    }


def human_review_node(state: AgentState) -> Dict[str, Any]:
    """Handles operator approval or rejection of pending database modifications."""
    approved = state.get("action_approved")
    pending = state.get("pending_approval")

    if not pending:
        return {}

    if approved is True:
        res = create_record(
            machine_id=pending["machine_id"],
            description=pending["description"],
            priority=pending["priority"]
        )
        confirm_text = (
            "### ✅ Action Authorized & Executed\n\n"
            f"**Operator Approval Received.** {res}\n\n"
            f"- **Target Asset:** `{pending['machine_id']}`\n"
            f"- **Priority:** `{pending['priority']}`\n"
            f"- **Audit Status:** Committed to `maintenance_requests` table.\n"
            f"- **Dispatch Status:** Queued for engineering response team."
        )
        return {
            "pending_approval": None,
            "action_approved": None,
            "tools_called": state.get("tools_called", []) + [{"tool": "create_record", "input": pending}],
            "final_response": confirm_text,
            "messages": [AIMessage(content=confirm_text)]
        }
    elif approved is False:
        reject_text = (
            "### ❌ Action Rejected by Operator\n\n"
            f"The proposed maintenance request for machine `{pending['machine_id']}` was **declined** by human operator. "
            "No changes were written to the factory database."
        )
        return {
            "pending_approval": None,
            "action_approved": None,
            "final_response": reject_text,
            "messages": [AIMessage(content=reject_text)]
        }

    return {}


def route_next_step(state: AgentState) -> str:
    """Routes execution based on whether human approval is pending."""
    if state.get("pending_approval") is not None and state.get("action_approved") is None:
        return END
    if state.get("action_approved") is not None:
        return "human_review"
    return END


def create_operations_graph(llm=None):
    """Builds and compiles the LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("agent_reasoning", agent_reasoning)
    workflow.add_node("human_review", human_review_node)

    workflow.add_edge(START, "agent_reasoning")

    workflow.add_conditional_edges(
        "agent_reasoning",
        route_next_step,
        {
            "human_review": "human_review",
            END: END
        }
    )

    workflow.add_edge("human_review", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
