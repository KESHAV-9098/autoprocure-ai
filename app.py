import streamlit as st
import sqlite3
import pandas as pd
from database import init_db, DB_NAME
from agent import run_autoprocure_agent
from tools import execute_razorpay_order, query_catalog

init_db()

st.set_page_config(page_title="AutoProcure AI - UAP Agentic Engine", layout="wide")
st.title("AutoProcure: Autonomous B2B Restock Engine")
st.caption("Razorpay AI Builder Track 01 Submission | NPCI UAP Protocol & Bounded Commerce")

# Controls Bar
col_actions, col_fail, col_reset = st.columns([3, 1.5, 1])
with col_actions:
    run_btn = st.button("Trigger Autonomous Agent Run", type="primary")
with col_fail:
    sim_fail = st.checkbox("Simulate Gateway Failure (Test Robustness)", value=False)
with col_reset:
    if st.button("🔄 Reset Demo State"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS inventory")
        cursor.execute("DROP TABLE IF EXISTS audit_logs")
        cursor.execute("DROP TABLE IF EXISTS reserve_vault")
        conn.commit()
        conn.close()
        init_db()
        st.rerun()

if run_btn:
    with st.spinner("Agent evaluating stock, negotiating catalogs, and enforcing UAP guardrails..."):
        if sim_fail:
            execute_razorpay_order("SKU-MS-02", 7, 1200, "TechSupply Direct", simulate_failure=True)
            st.warning("Graceful failure handling demonstrated: API failure intercepted and safely rolled back.")
        else:
            run_autoprocure_agent()
            st.success("Full catalog evaluation complete.")
        st.rerun()

st.divider()

# NPCI UAP Vault & Performance Metrics
conn = sqlite3.connect(DB_NAME)
df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
df_logs = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC", conn)
df_vault = pd.read_sql_query("SELECT * FROM reserve_vault WHERE id = 1", conn)
conn.close()

vault_bal = df_vault["balance_inr"].iloc[0] if not df_vault.empty else 0.0
daily_spent = df_vault["daily_spent_inr"].iloc[0] if not df_vault.empty else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("NPCI UAP Reserve Balance", f"₹{vault_bal:,.2f}", delta=f"-₹{daily_spent:,.2f} spent" if daily_spent > 0 else None)
m2.metric("Items Needing Restock", len(df_inv[df_inv["current_stock"] <= df_inv["reorder_threshold"]]))
m3.metric("Auto-Executed Orders", len(df_logs[df_logs["status"] == "SUCCESS"]))
m4.metric("Gated / Handled Exceptions", len(df_logs[df_logs["status"].isin(["BLOCKED", "FAILED_GRACEFUL"])]))

st.divider()

# Tables
col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Store Inventory (20 Items)")
    st.dataframe(df_inv, use_container_width=True, height=450)

with col2:
    st.subheader("Live UAP Audit Trail & Telemetry")
    # Make payment links clickable directly in the table
    st.dataframe(
        df_logs,
        column_config={
            "details": st.column_config.LinkColumn(
                "Payment / Log Details",
                display_text=r"https://rzp\.io/i/([a-zA-Z0-9]+)"
            )
        },
        use_container_width=True,
        height=450
    )

# Escalation Panel
df_pending = df_logs[df_logs["status"] == "BLOCKED"]
if not df_pending.empty:
    st.warning("Action Required: High-Value or Restricted Transactions Awaiting Authorization")
    for _, row in df_pending.iterrows():
        c_desc, c_btn = st.columns([4, 1])
        with c_desc:
            st.write(f"SKU: **{row['sku']}** | Amount: **INR {row['amount_inr']:,.2f}** | Reason: *{row['details']}*")
        with c_btn:
            if st.button(f"Approve {row['sku']}", key=f"btn_{row['id']}"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("UPDATE audit_logs SET status = 'RESOLVED' WHERE id = ?", (row['id'],))
                conn.commit()
                conn.close()
                
                cat_info = query_catalog(row["sku"])
                if cat_info:
                    units = int(row['amount_inr'] / cat_info['unit_price_inr'])
                    res = execute_razorpay_order(row["sku"], units, cat_info["unit_price_inr"], cat_info["supplier"], force_approved=True)
                st.rerun()