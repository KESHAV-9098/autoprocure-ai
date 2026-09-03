MAX_AUTO_SPEND_INR = 20000.0  # Cap for automated purchasing
APPROVED_SUPPLIERS = ["TechSupply Direct", "GadgetWholesale Ltd"]

def validate_purchase_policy(supplier: str, total_amount_inr: float):
    if supplier not in APPROVED_SUPPLIERS:
        return False, f"Supplier '{supplier}' is not in the approved whitelist."
    
    if total_amount_inr > MAX_AUTO_SPEND_INR:
        return False, f"Total ₹{total_amount_inr:,.2f} exceeds max auto-spend limit of ₹{MAX_AUTO_SPEND_INR:,.2f}. Human approval required."
    
    return True, "Policy checks passed: Authorized for automated checkout."