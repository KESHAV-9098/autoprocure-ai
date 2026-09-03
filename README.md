# AutoProcure AI: Bounded Agent-to-Agent Autonomous B2B Restock Engine

 APP LINK: https://autoprocure-ai.streamlit.app/

An autonomous agentic procurement engine built for the **Razorpay AI Builder Track 01 (AI Growth & Agentic Commerce)** track.

## 📌 Problem Statement
Manual inventory monitoring and supplier purchase order generation lead to supply-chain friction, stockouts, and human error. AutoProcure enables autonomous machine-to-machine commerce by parsing machine-readable supplier catalogs and placing test orders via Razorpay APIs under strict deterministic policy guardrails.

---

## 🚀 Key Features & "The Bar" Alignment
* **Autonomous Purchasing:** Automatically identifies low-stock items against predefined thresholds and creates live Razorpay test-mode orders.
* **Deterministic Guardrails & Policy Engine:** Strict ceiling checks (e.g., maximum auto-spend ₹10,000) and verified supplier allowlists.
* **Human-in-the-Loop Escalation:** Transactions exceeding safety thresholds are automatically halted, logged as `BLOCKED`, and gated behind human supervisor approval.
* **Traceable Audit Log:** End-to-end audit trail tracking every agent reasoning step, tool call, order ID, and failure state in SQLite.

---

## 🛠️ Architecture & Tech Stack
* **LLM Reasoning Engine:** Groq Cloud (`openai/gpt-oss-20b` / `llama-3.1-8b-instant`)
* **Payment Layer:** Razorpay Python SDK (Test Mode Orders & Invoicing)
* **Storage & Audit:** SQLite3
* **Dashboard & Visualizer:** Streamlit
