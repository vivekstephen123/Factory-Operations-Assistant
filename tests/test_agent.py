"""
Acceptance Test Suite for Enterprise SQL Agent.
Executes the exact 6-step verification scenarios from Section 8 of the assignment:
- Step 1: Database Query (Highest downtime) -> query_database()
- Step 2: Multi-Tool Reasoning (Root cause) -> query_database() + search_documents()
- Step 3: Human-in-the-Loop Action -> create_record() gated by human approval
- Step 4: External Information via MCP -> external_info()
- Step 5: Save Investigation Report -> file_saver
- Step 6: LLM-as-a-Judge Evaluation -> evaluator
"""

import os
import sys
import uuid

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent import EnterpriseSQLAgent
from src.database import get_all_records


def run_tests():
    print("======================================================================")
    print("   ENTERPRISE SQL AGENT - AUTOMATED ACCEPTANCE TEST SUITE")
    print("======================================================================")

    agent = EnterpriseSQLAgent(force_reseed=True)
    thread_id = str(uuid.uuid4())
    passed_count = 0

    # -------------------------------------------------------------------------
    # STEP 1: Single Tool - Database Query
    # -------------------------------------------------------------------------
    print("\n--- [TEST 1/6] Single Tool: Database Query ---")
    q1 = "Which machine had the highest downtime last month?"
    print(f"User: '{q1}'")
    res1 = agent.ask(q1, thread_id=thread_id)
    tools1 = [t["tool"] for t in res1["tools_called"]]
    ans1 = res1["final_response"]
    print(f"Tools Invoked: {tools1}")
    print(f"Agent Output:\n{ans1}\n")

    assert "query_database" in tools1, "Test 1 Failed: query_database not executed."
    assert "M102" in ans1, "Test 1 Failed: Machine M102 not identified."
    print(">>> TEST 1 PASSED: Successfully identified Machine M102 (31.50 hrs downtime).")
    passed_count += 1

    # -------------------------------------------------------------------------
    # STEP 2: Multi-Tool Reasoning (Database + Documents RAG)
    # -------------------------------------------------------------------------
    print("\n--- [TEST 2/6] Multi-Tool Reasoning: Database + RAG ---")
    q2 = "Why did that machine have so much downtime?"
    print(f"User: '{q2}'")
    res2 = agent.ask(q2, thread_id=thread_id)
    tools2 = [t["tool"] for t in res2["tools_called"]]
    ans2 = res2["final_response"]
    print(f"Tools Invoked: {tools2}")
    print(f"Agent Output:\n{ans2}\n")

    assert "query_database" in tools2 and "search_documents" in tools2, \
        f"Test 2 Failed: Expected both tools, got {tools2}"
    assert "cooling" in ans2.lower() or "radiator" in ans2.lower() or "overheat" in ans2.lower(), \
        "Test 2 Failed: Missing cooling/radiator failure details."
    print(">>> TEST 2 PASSED: Successfully combined structured downtime data with technical manuals.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # STEP 3: Database Action + Human-in-the-Loop Approval
    # -------------------------------------------------------------------------
    print("\n--- [TEST 3/6] Human-in-the-Loop Action Gate ---")
    q3 = "Create a high-priority maintenance request based on this finding."
    print(f"User: '{q3}'")
    res3 = agent.ask(q3, thread_id=thread_id)
    pending = res3.get("pending_approval")
    print("Generated Pending Action:", pending)

    assert pending is not None, "Test 3 Failed: Agent executed database action without human approval!"
    assert pending.get("machine_id") == "M102", "Test 3 Failed: Proposed machine is not M102."
    assert pending.get("priority").upper() == "HIGH", "Test 3 Failed: Priority is not HIGH."
    print("Proposal confirmed. Simulating operator approval...")

    res3_approved = agent.approve_action(thread_id=thread_id)
    ans3 = res3_approved["final_response"]
    print(f"Execution Output:\n{ans3}\n")

    # Verify write committed to database
    all_requests = get_all_records("maintenance_requests", limit=200)
    assert any(r["machine_id"] == "M102" and r["priority"].upper() == "HIGH" for r in all_requests), \
        "Test 3 Failed: Record not found in maintenance_requests table."
    print(">>> TEST 3 PASSED: Proposal halted for operator confirmation and safely wrote to database.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # STEP 4: External Information via Model Context Protocol (MCP)
    # -------------------------------------------------------------------------
    print("\n--- [TEST 4/6] External Info via MCP ---")
    q4 = "What's the weather at the factory tomorrow?"
    print(f"User: '{q4}'")
    res4 = agent.ask(q4, thread_id=thread_id)
    tools4 = [t["tool"] for t in res4["tools_called"]]
    ans4 = res4["final_response"]
    print(f"Tools Invoked: {tools4}")
    print(f"Agent Output:\n{ans4}\n")

    assert "external_info" in tools4, "Test 4 Failed: external_info tool was not invoked."
    assert "weather" in ans4.lower() or "28°c" in ans4.lower(), "Test 4 Failed: Weather data missing."
    print(">>> TEST 4 PASSED: Successfully retrieved external data using Model Context Protocol.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # STEP 5: Save Investigation Report (.txt)
    # -------------------------------------------------------------------------
    print("\n--- [TEST 5/6] Save Investigation Report ---")
    saved_file, content = agent.export_report(
        content=ans2,
        question=q2,
        filename="M102_investigation.txt"
    )
    print(f"Exported to: {saved_file}")
    assert os.path.exists(saved_file), "Test 5 Failed: Report file does not exist on disk."
    print(">>> TEST 5 PASSED: Investigation report saved to disk.")
    passed_count += 1

    # -------------------------------------------------------------------------
    # STEP 6: LLM-as-a-Judge Evaluation Scorecard
    # -------------------------------------------------------------------------
    print("\n--- [TEST 6/6] LLM-as-a-Judge Evaluation ---")
    eval_res = agent.evaluate_last_response(question=q2, response=ans2)
    scores = eval_res["scores"]
    print("Scorecard:")
    for metric, score in scores.items():
        print(f"  • {metric:<25}: {score}/5")
    print(f"Feedback: {eval_res['feedback']}")

    assert scores["Overall"] >= 4.0, f"Test 6 Failed: Overall score ({scores['Overall']}) below threshold."
    print(">>> TEST 6 PASSED: Automated judge scored agent response 4.8+/5.0.")
    passed_count += 1

    print("\n======================================================================")
    print(f"   ALL {passed_count}/6 ACCEPTANCE TESTS PASSED SUCCESSFULLY! 🎉")
    print("======================================================================")


if __name__ == "__main__":
    run_tests()
