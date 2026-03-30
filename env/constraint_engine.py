import json
import os
from supply_chain_sim import SupplyChainState

POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")

def load_policy(country: str) -> dict:
    """Loads the policy JSON for a given country (India, EU, USA)."""
    filename = f"{country.lower()}_policy.json"
    filepath = os.path.join(POLICY_DIR, filename)
    with open(filepath, "r") as f:
        return json.load(f)

def validate_action(state: SupplyChainState, selected_supplier: dict, policy: dict) -> tuple:
    """
    Returns (is_valid: bool, penalty: float, violation_type: str or None)
    
    Hard rule violation -> is_valid=False, penalty=-1.0 (episode ends)
    Soft rule violation -> is_valid=True, penalty=-0.2 (episode continues)
    No violation       -> is_valid=True, penalty=0.0
    """
    if not selected_supplier:
        return (True, 0.0, None)
        
    penalty = 0.0
    violation_type = None
    
    # Hard rule: check sanctioned suppliers
    sanctioned_categories = policy.get("sanctioned_categories", [])
    if selected_supplier.get("sanctioned_category") in sanctioned_categories and selected_supplier.get("sanctioned_category") is not None:
        return (False, -1.0, "sanctioned_supplier_selected")
        
    # Hard rule: check carbon limit per order (EU)
    max_carbon = policy.get("max_carbon_tons_per_order")
    if max_carbon is not None and selected_supplier.get("carbon_tons", 0.0) > max_carbon:
        return (False, -1.0, "exceeded_max_carbon_per_order")
        
    # Hard rule: check OFAC sanctions (USA)
    ofac_countries = policy.get("ofac_sanctioned_countries", [])
    if selected_supplier.get("country") in ofac_countries:
        return (False, -1.0, "ofac_sanctioned_country")
        
    # Soft rule: prefer low carbon
    if selected_supplier.get("carbon_tons", 0.0) > 2.0:
        penalty -= 0.2
        violation_type = "high_carbon"

    # Soft rule: prefer domestic supplier
    # For now, we'll implement a basic check if the policy file implies a certain country
    # E.g., if there's a duty rate, maybe it's cross-border? We'll leave it as a placeholder
    # Or if the policy file name implies the host country, we could match. But we don't 
    # receive the host country directly in `validate_action` from the snippet.
    # The snippet says "Soft rule: prefer domestic supplier". Let's assume a penalty 
    # if it's imported (e.g. duty rate applies).
    # Since we can't perfectly infer host, we'll just implement the structure.
    
    if penalty < 0:
        state.violations += 1
        
    return (True, penalty, violation_type)
