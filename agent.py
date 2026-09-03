import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tools import get_low_stock_items, query_catalog, execute_razorpay_order
from database import log_audit

load_dotenv()

def run_autoprocure_agent():
    groq_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model="openai/gpt-oss-20b", api_key=groq_key)
    
    low_stock_items = get_low_stock_items()
    if not low_stock_items:
        return "All inventory levels are healthy. No orders triggered."
    
    results = []
    
    for item in low_stock_items:
        sku = item["sku"]
        needed_units = item["target"] - item["current_stock"]
        catalog_info = query_catalog(sku)
        
        if not catalog_info:
            log_audit(sku, "CATALOG_LOOKUP", "Supplier Not Found", "FAILED", details="SKU not present in catalog.")
            continue
            
        units_to_order = max(needed_units, catalog_info["min_order_qty"])
        supplier = catalog_info["supplier"]
        unit_price = float(catalog_info["unit_price_inr"])
        
        # Negotiate volume discount tier
        bulk_rule = catalog_info.get("bulk_discount")
        negotiated_note = "Standard catalog rate"
        if bulk_rule and units_to_order >= bulk_rule["min_qty"]:
            discount_pct = bulk_rule["discount_pct"]
            unit_price = unit_price * (1 - (discount_pct / 100.0))
            negotiated_note = f"Volume tier unlocked: {discount_pct}% discount applied"

        total_price = units_to_order * unit_price
        
        prompt = (
            f"You are AutoProcure Agent. Assess restocking SKU: {sku}.\n"
            f"Current Stock: {item['current_stock']}, Needed: {needed_units}, Order: {units_to_order} units.\n"
            f"Pricing Terms: {negotiated_note} -> Effective Rate: INR {unit_price:.2f}/unit. Total: INR {total_price:.2f}.\n"
            f"Supplier: {supplier}.\n"
            f"Output a concise 1-sentence reasoning confirming this procurement plan."
        )
        
        response = llm.invoke(prompt)
        decision_reasoning = response.content.strip()
        
        exec_result = execute_razorpay_order(sku, units_to_order, unit_price, supplier)
        results.append({
            "sku": sku,
            "units": units_to_order,
            "pricing": negotiated_note,
            "reasoning": decision_reasoning,
            "result": exec_result
        })
        
    return results