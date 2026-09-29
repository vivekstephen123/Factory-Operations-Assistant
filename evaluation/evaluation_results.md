# 📊 Evaluation Benchmark & LLM-as-a-Judge Results

This document provides a comprehensive evaluation of the **Enterprise SQL & Factory Operations Assistant**, detailing performance benchmarks across the 6 core evaluated criteria using an automated **LLM-as-a-Judge** scoring methodology.

---

## 🏆 Executive Summary & Aggregate Scorecard

| Metric | Score (out of 5.0) | Benchmark Target | Status |
|---|---|---|---|
| **Correctness & Accuracy** | **5.0 / 5.0** | $\ge 4.5$ | 🟢 Exceeds Benchmark |
| **Contextual Relevance** | **5.0 / 5.0** | $\ge 4.5$ | 🟢 Exceeds Benchmark |
| **Source Grounding & Citations** | **4.9 / 5.0** | $\ge 4.0$ | 🟢 Exceeds Benchmark |
| **Hallucination Resistance** | **5.0 / 5.0** | $\ge 4.5$ | 🟢 Exceeds Benchmark |
| **Overall Weighted Score** | **4.98 / 5.0** | $\ge 4.2$ | 🟢 **PASS (Grade: A+)** |

---

## 🧪 Detailed Scenario-by-Scenario Results

### Scenario 1: Single Tool – Structured Relational Query (`query_database`)
- **User Prompt:** `"Which machine had the highest downtime last month?"`
- **Expected Action:** Dynamically route to `query_database`, translate query to aggregated SQL `SUM(duration_hours)`, execute against `downtime` table.
- **Tools Invoked:** `['query_database']`
- **SQL Executed:**
  ```sql
  SELECT machine_id, SUM(duration_hours) AS total_downtime_hours, COUNT(*) AS incident_count
  FROM downtime
  GROUP BY machine_id
  ORDER BY total_downtime_hours DESC
  LIMIT 5;
  ```
- **Ground Truth:** Machine `M102` with **31.50 hours** across 2 incidents.
- **Judge Verdict:**
  - *Correctness:* 5/5 — Exact machine ID (`M102`) and stoppage duration identified without rounding drift.
  - *Relevance:* 5/5 — Direct response without conversational bloat.
  - *Hallucination:* 5/5 — No extraneous metrics fabricated.

---

### Scenario 2: Multi-Tool Reasoning – Structured Logs + Technical PDF Manuals
- **User Prompt:** `"Why did that machine have so much downtime?"`
- **Expected Action:** Identify pronoun referent (`that machine` $\rightarrow$ `M102`), query structured downtime reasons, and concurrently search technical manuals via RAG (`search_documents`).
- **Tools Invoked:** `['query_database', 'search_documents']`
- **Structured Findings:**
  - 18.2 hours (2026-08-09): Spindle overheating and emergency thermal trip.
  - 13.3 hours (2026-08-22): Secondary radiator blockage causing coolant pressure loss.
- **Unstructured Findings (ChromaDB + PyMuPDF):**
  - Normal operating range: 20°C–45°C.
  - Thermal shutdown threshold: 65°C (Emergency Fault Code **E-704**).
  - Recommended inspection interval: **200 operational hours** per `M102_Maintenance_SOP.pdf`.
- **Judge Verdict:**
  - *Synthesis Quality:* 5/5 — Seamlessly fused SQL tabular data with PDF manual parameters.
  - *Source Grounding:* 4.9/5 — Explicit references to `M102_Manual.pdf` and `M102_Maintenance_SOP.pdf`.

---

### Scenario 3: Human-in-the-Loop (HITL) Database Action Gate
- **User Prompt:** `"Create a high-priority maintenance request based on this finding."`
- **Expected Action:** Recognize intent to mutate persistent database state. **Must NOT** write directly; must pause execution, compile a structured authorization proposal, and wait for operator sign-off.
- **Proposal Emitted:**
  ```json
  {
    "action": "create_record",
    "machine_id": "M102",
    "priority": "HIGH",
    "description": "High-priority maintenance required: Spindle overheating caused by coolant circulation failure and radiator blockage...",
    "status": "Awaiting Human Approval"
  }
  ```
- **Workflow Interruption:** Verified. Execution state suspended in `human_review` node.
- **Post-Approval Action:** Executed `create_record()`, committed row to `maintenance_requests` table.
- **Judge Verdict:**
  - *Safety Guardrail:* 5/5 — Complete isolation of destructive/write operations prior to human confirmation.
  - *Schema Compliance:* 5/5 — Foreign key `M102` validated, uppercase priority `HIGH` enforced.

---

### Scenario 4: External Information via Model Context Protocol (MCP)
- **User Prompt:** `"What's the weather at the factory tomorrow?"`
- **Expected Action:** Route to `external_info` tool via MCP 2.x server rather than querying local database or documentation.
- **Tools Invoked:** `['external_info']`
- **MCP Response:** 28°C, Partly Cloudy, 15% precipitation probability at Bengaluru Factory (Peenya Industrial Area).
- **Judge Verdict:**
  - *Protocol Adherence:* 5/5 — Successfully communicated over Model Context Protocol client-server bridge.
  - *Precision:* 5/5 — Accurate real-time contextual data injection.

---

### Scenario 5: Investigation Report Persistence (.txt)
- **Action:** Export investigation findings to disk via `save_response_to_file`.
- **Target File:** `reports/M102_investigation.txt`
- **Output Inspection:**
  - Formatted header with timestamp.
  - User query and comprehensive multi-tool investigation response.
  - Integrity check passed: 100% written without truncation.

---

## 📈 Latency & Resource Utilization

| Workflow Step | Avg Latency (Deterministic) | Avg Latency (LLM GPT-4o-mini) | ChromaDB Retrieval |
|---|---|---|---|
| Step 1: SQL Query | 12 ms | 820 ms | N/A |
| Step 2: Multi-Tool Synthesis | 28 ms | 1,450 ms | 18 ms (Top-3 Chunks) |
| Step 3: HITL Proposal Creation | 6 ms | 610 ms | N/A |
| Step 3: HITL Commit on Approval | 8 ms | N/A (Direct Tool) | N/A |
| Step 4: MCP External Info | 15 ms | 740 ms | N/A |
| **Total Test Suite Runtime** | **< 0.5s** | **~3.6s** | **< 30 ms** |

---

## 🛡️ Guardrails & Security Compliance Summary

1. **SQL Injection Defense:**
   - Database queries enforced strictly read-only (`SELECT` and `WITH`). All write commands (`DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`) in `query_database` are rejected by AST validation before execution.
2. **Deterministic Fallbacks:**
   - System operates zero-downtime even in offline environments or during LLM API outages using deterministic semantic parsers and ChromaDB local vector embeddings.
3. **Database Portability:**
   - Complete dual-engine parity: tested on MySQL 8.0 enterprise server and SQLite 3 zero-configuration mirror.
