import os
import json
import sqlite3
import razorpay
from dotenv import load_dotenv
from database import DB_NAME, log_audit, deduct_reserve_vault
from guardrails import validate_purchase_policy

load_dotenv()

RAZORPAY_KEY = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = None
if RAZORPAY_KEY and RAZORPAY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

def get_low_stock_items():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sku, item_name, current_stock, reorder_threshold, target_stock FROM inventory WHERE current_stock <= reorder_threshold")
    rows = cursor.fetchall()
    conn.close()
    return [{"sku": r[0], "item_name": r[1], "current_stock": r[2], "threshold": r[3], "target": r[4]} for r in rows]

def query_catalog(sku: str):
    with open("catalog.json", "r") as f:
        catalog = json.load(f)
    for item in catalog:
        if item["sku"] == sku:
            return item
    return None

def execute_razorpay_order(sku: str, units: int, unit_price: float, supplier: str, force_approved: bool = False, simulate_failure: bool = False):
    total_inr = units * unit_price
    
    # 1. Check Policy Engine
    is_valid, reason = validate_purchase_policy(supplier, total_inr)
    if not is_valid and not force_approved:
        log_audit(sku, "POLICY_GATE", "Hold Execution", "BLOCKED", amount_inr=total_inr, details=reason)
        return {"status": "BLOCKED", "reason": reason, "amount_inr": total_inr}

    # 2. Check NPCI UAP Reserve Balance
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance_inr, daily_spent_inr, daily_limit_inr FROM reserve_vault WHERE id = 1")
    vault = cursor.fetchone()
    conn.close()

    if vault:
        balance, daily_spent, daily_limit = vault
        if total_inr > balance:
            reason = f"UAP Reserve Pay Insufficient: Available ₹{balance:,.2f}, required ₹{total_inr:,.2f}."
            log_audit(sku, "UAP_VAULT_DEPLETED", "Decline Action", "BLOCKED", amount_inr=total_inr, details=reason)
            return {"status": "BLOCKED", "reason": reason, "amount_inr": total_inr}

    # 3. Simulate Graceful Failure
    if simulate_failure:
        log_audit(sku, "GATEWAY_TIMEOUT", "Simulated 504 Gateway Timeout -> Rolling back state", "FAILED_GRACEFUL", amount_inr=total_inr, details="Razorpay sandbox simulation: Network timeout. Fallback triggered; no state corrupted.")
        return {"status": "FAILED_GRACEFUL", "reason": "Simulated Gateway Timeout (Circuit Breaker Handled)", "amount_inr": total_inr}

    # 4. Standard Razorpay Order & Payment Link Execution
    try:
        if not client:
            raise ValueError("Razorpay credentials missing in .env")
            
        receipt_id = f"uap_{sku.lower()}_{int(total_inr)}"
        order_payload = {
            "amount": int(total_inr * 100),
            "currency": "INR",
            "receipt": receipt_id,
            "notes": {
                "protocol": "NPCI-UAP-v1",
                "agent": "AutoProcure-AI",
                "sku": sku,
                "units": str(units),
                "supplier": supplier
            }
        }
        
        # Create Order on Razorpay
        order_response = client.order.create(data=order_payload)
        order_id = order_response.get("id")

        # Create Payment Link tied to this order
        payment_link_payload = {
            "amount": int(total_inr * 100),
            "currency": "INR",
            "accept_partial": False,
            "reference_id": order_id,
            "description": f"AutoProcure Settlement: {units}x {sku} via {supplier}",
            "customer": {
                "name": "AutoProcure Store Vault",
                "email": "procure@autoprocure.internal",
                "contact": "+919876543210"
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {
                "sku": sku,
                "order_id": order_id
            }
        }
        link_response = client.payment_link.create(data=payment_link_payload)
        payment_url = link_response.get("short_url")
        
        # Deduct UAP Vault & Update Inventory
        deduct_reserve_vault(total_inr)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET current_stock = current_stock + ? WHERE sku = ?", (units, sku))
        conn.commit()
        conn.close()
        
        log_audit(sku, "ORDER_CREATED", "Automated Checkout", "SUCCESS", order_id=order_id, amount_inr=total_inr, details=f"Payment Link: {payment_url}")
        return {"status": "SUCCESS", "order_id": order_id, "payment_url": payment_url, "amount_inr": total_inr}

    except Exception as e:
        log_audit(sku, "API_FAILURE", "Exception Handled", "FAILED", amount_inr=total_inr, details=str(e))
        return {"status": "FAILED", "reason": str(e), "amount_inr": total_inr}