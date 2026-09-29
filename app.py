"""
Factory Operations Assistant - Streamlit Application.
Built with LangGraph, RAG (Chroma), MCP, Human-in-the-loop, and LLM-as-a-Judge Evaluation.
"""

import os
import sys
import uuid
import streamlit as st
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.database import init_database, get_all_records, get_active_engine_name, is_mysql_available
    from src.graph import create_operations_graph, get_llm
except ImportError:
    from database.db import init_database, get_all_records, get_active_engine_name, is_mysql_available
    from agent.graph import create_operations_graph, get_llm

try:
    from agent.evaluator import evaluate_response
    from agent.file_saver import save_response_to_file
except ImportError:
    pass

from rag.rag_engine import init_rag_store
from langchain_core.messages import HumanMessage

st.set_page_config(
    page_title="Factory Operations Assistant",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .tool-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        background-color: #E0E7FF;
        color: #3730A3;
        border: 1px solid #C7D2FE;
    }
    .approval-box {
        background-color: #FEF3C7;
        border-left: 5px solid #F59E0B;
        padding: 1rem;
        border-radius: 0.375rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def setup_resources():
    init_database(force_reseed=False)
    init_rag_store(force_reindex=False)
    try:
        from screenshots.generate_screenshots import generate_all
        generate_all()
    except Exception:
        pass
    return True

setup_resources()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None

if "tools_called_history" not in st.session_state:
    st.session_state.tools_called_history = []


# Sidebar
with st.sidebar:
    st.header("⚙️ System Control")
    
    model_provider = st.selectbox(
        "AI Reasoning Engine",
        options=["demo", "gemini", "openai", "groq"],
        format_func=lambda x: {
            "demo": "🚀 Built-in Demo Engine (Fast & No API Key Needed)",
            "gemini": "✨ Google Gemini (gemini-3.5-flash)",
            "openai": "🧠 OpenAI (GPT-4o-mini)",
            "groq": "⚡ Groq (gpt-oss-120b)"
        }[x]
    )

    api_key_input = ""
    if model_provider != "demo":
        env_key_name = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY"
        }[model_provider]
        
        default_env = os.environ.get(env_key_name, "")
        api_key_input = st.text_input(
            f"{model_provider.upper()} API Key",
            type="password",
            value=default_env,
            help=f"Enter key or set {env_key_name} in environment."
        )

    current_llm = get_llm(model_provider, api_key_input)
    graph = create_operations_graph(llm=current_llm)

    st.divider()

    st.subheader("🧪 6-Step Acceptance Test")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("Step 1: DB Query", use_container_width=True):
            st.session_state.test_input = "Which machine had the highest downtime last month?"
        if st.button("Step 3: Create Ticket", use_container_width=True):
            st.session_state.test_input = "Create a high-priority maintenance request based on this finding."
    with col_s2:
        if st.button("Step 2: Multi-Tool (DB+RAG)", use_container_width=True):
            st.session_state.test_input = "Why did that machine have so much downtime?"
        if st.button("Step 4: Weather (MCP)", use_container_width=True):
            st.session_state.test_input = "What's the weather at the factory tomorrow?"

    if st.button("Clear Chat / Reset Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_approval = None
        st.session_state.last_query = ""
        st.session_state.last_response = ""
        st.session_state.last_evaluation = None
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    st.divider()

    # Database Live Inspector & Engine Info
    st.subheader("🗄️ Relational Database")
    st.caption(f"**Active Engine**: `{get_active_engine_name()}`")
    
    with st.expander("⚙️ MySQL 8.0 Connection Settings", expanded=False):
        mysql_u = st.text_input("MySQL User", value=os.environ.get("MYSQL_USER", "root"))
        mysql_p = st.text_input("MySQL Password", type="password", value=os.environ.get("MYSQL_PASSWORD", ""))
        mysql_db = st.text_input("Database Name", value=os.environ.get("MYSQL_DATABASE", "factory_ops_db"))
        if st.button("Connect & Migrate MySQL Schema", use_container_width=True):
            os.environ["MYSQL_USER"] = mysql_u
            os.environ["MYSQL_PASSWORD"] = mysql_p
            os.environ["MYSQL_DATABASE"] = mysql_db
            try:
                init_database(force_reseed=True)
                st.success("Successfully connected to MySQL and migrated schema!")
                st.rerun()
            except Exception as ex:
                st.error(f"MySQL Connection Error: {ex}")

    db_table = st.selectbox("Inspect Table:", ["machines", "downtime", "maintenance_requests"])
    rows = get_all_records(db_table)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=200)
    else:
        st.caption("No records.")

    st.divider()
    st.caption("Factory Operations Assistant • LangGraph + RAG + MCP + HITL")


# Main UI
st.markdown('<div class="main-title">⚙️ Factory Operations Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Intelligent plant assistant powered by <b>LangGraph</b>, <b>RAG Manuals</b>, '
    '<b>Model Context Protocol (MCP)</b>, and <b>Human-in-the-Loop</b> governance.</div>',
    unsafe_allow_html=True
)

with st.expander("🛠️ Active Tool Capabilities (4 Tools Only)", expanded=False):
    t_c1, t_c2, t_c3, t_c4 = st.columns(4)
    with t_c1:
        st.markdown("**1. `query_database`**")
        st.caption("Plain English questions translated to SQL against MySQL/SQLite tables.")
    with t_c2:
        st.markdown("**2. `search_documents`**")
        st.caption("RAG vector search over PDF technical manuals, SOPs, and safety docs.")
    with t_c3:
        st.markdown("**3. `create_record`**")
        st.caption("Insert maintenance tickets, subject to explicit human approval.")
    with t_c4:
        st.markdown("**4. `external_info`**")
        st.caption("Live external weather and route navigation via Model Context Protocol.")

# Chat history
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        if msg.get("tools"):
            st.markdown(
                "".join([f'<span class="tool-badge">🔧 Tool: {t}</span>' for t in msg["tools"]]),
                unsafe_allow_html=True
            )
        st.markdown(msg["content"])

# Human-in-the-loop dialog
if st.session_state.pending_approval:
    pending = st.session_state.pending_approval
    st.markdown('<div class="approval-box">', unsafe_allow_html=True)
    st.markdown("### ⚠️ Human-in-the-Loop Action Approval Required")
    st.markdown(
        f"The agent has prepared a database insertion request:\n\n"
        f"- **Target Table**: `maintenance_requests`\n"
        f"- **Machine ID**: `{pending.get('machine_id', 'M102')}`\n"
        f"- **Issue Description**: {pending.get('description', '')}\n"
        f"- **Priority**: `{pending.get('priority', 'High')}`\n\n"
        f"**Do you approve inserting this record into the database?**"
    )
    col_app, col_rej = st.columns([1, 4])
    with col_app:
        if st.button("✅ Approve & Insert", type="primary", use_container_width=True):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            result = graph.invoke({"action_approved": True}, config=config)
            
            final_text = result.get("final_response", "Action executed.")
            tools = [t["tool"] for t in result.get("tools_called", [])]

            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text,
                "tools": tools if tools else ["create_record"]
            })
            st.session_state.pending_approval = None
            st.session_state.last_response = final_text
            st.rerun()

    with col_rej:
        if st.button("❌ Reject / Cancel", use_container_width=False):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            result = graph.invoke({"action_approved": False}, config=config)
            
            final_text = result.get("final_response", "Action rejected by operator.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text,
                "tools": []
            })
            st.session_state.pending_approval = None
            st.session_state.last_response = final_text
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Input handling
user_query = st.chat_input("Ask a question about machines, manuals, weather, or maintenance...")

if getattr(st.session_state, "test_input", None):
    user_query = st.session_state.test_input
    st.session_state.test_input = None

if user_query:
    st.session_state.last_query = user_query
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Agent reasoning & selecting tools..."):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            graph_input = {
                "messages": [HumanMessage(content=user_query)],
                "tools_called": []
            }
            res = graph.invoke(graph_input, config=config)

            pending = res.get("pending_approval")
            tools = [t["tool"] for t in res.get("tools_called", [])]
            final_text = res.get("final_response") or (res["messages"][-1].content if res.get("messages") else "")

            if pending:
                st.session_state.pending_approval = pending

            st.session_state.last_response = final_text

            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text,
                "tools": tools
            })
            st.rerun()

st.divider()

col_act1, col_act2, col_spacer = st.columns([1.5, 1.8, 3.5])

with col_act1:
    if st.button("💾 Save Response (.TXT)", use_container_width=True, disabled=not bool(st.session_state.last_response)):
        filepath, file_text = save_response_to_file(
            content=st.session_state.last_response,
            question=st.session_state.last_query
        )
        st.success(f"Saved to: `{os.path.basename(filepath)}`")
        st.download_button(
            label="📥 Download .txt File",
            data=file_text,
            file_name=os.path.basename(filepath),
            mime="text/plain",
            use_container_width=True
        )

with col_act2:
    if st.button("🎯 Evaluate Response (LLM Judge)", use_container_width=True, disabled=not bool(st.session_state.last_response)):
        with st.spinner("Evaluating response against reference operations knowledge..."):
            eval_result = evaluate_response(
                question=st.session_state.last_query,
                agent_answer=st.session_state.last_response,
                llm=current_llm
            )
            st.session_state.last_evaluation = eval_result

if st.session_state.last_evaluation:
    ev = st.session_state.last_evaluation
    scores = ev["scores"]

    st.markdown("### 📋 Response Evaluation Scorecard")
    st.caption("Independent evaluation using **LLM-as-a-Judge** against factory reference benchmarks.")

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    sc1.metric("Correctness", f"{scores['Correctness']} / 5")
    sc2.metric("Relevance", f"{scores['Relevance']} / 5")
    sc3.metric("Uses Correct Source", f"{scores['Uses correct source']} / 5")
    sc4.metric("Hallucination Resistance", f"{scores['Hallucination resistance']} / 5")
    sc5.metric("Overall Score", f"{scores['Overall']} / 5")

    st.info(f"**Judge Feedback**: {ev['feedback']}")
    with st.expander("🔍 View Evaluation Reference Benchmark", expanded=False):
        st.markdown(f"**Reference Ground Truth:**\n\n{ev['reference_info']}")
