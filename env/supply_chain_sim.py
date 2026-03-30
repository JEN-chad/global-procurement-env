from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class SupplyChainState:
    inventory: Dict[str, float] = field(default_factory=lambda: {"steel": 0.0, "chips": 0.0, "fabric": 0.0})
    suppliers: List[Dict[str, Any]] = field(default_factory=list)
    budget: float = 200000.0
    lead_days: int = 0
    carbon: float = 0.0
    step_count: int = 0
    violations: int = 0

def apply_action(state: SupplyChainState, action: int, available_suppliers: list) -> dict:
    """
    Applies an action to the state and returns a result dict with:
    - cost_incurred (float)
    - lead_days_added (int)
    - carbon_added (float)
    - action_label (str)
    - selected_supplier (dict or None)
    """
    result = {
        "cost_incurred": 0.0,
        "lead_days_added": 0,
        "carbon_added": 0.0,
        "action_label": "",
        "selected_supplier": None
    }
    
    # Filter suppliers that are currently available
    valid_suppliers = [s for s in available_suppliers if s.get("available", True)]
    
    if action == 0:  # approve_cheapest
        result["action_label"] = "approve_cheapest"
        if valid_suppliers:
            supplier = min(valid_suppliers, key=lambda x: x["price_usd"])
            result["selected_supplier"] = supplier
            
            result["cost_incurred"] = float(supplier["price_usd"])
            result["lead_days_added"] = int(supplier["lead_days"])
            result["carbon_added"] = float(supplier["carbon_tons"])
            
            state.budget -= result["cost_incurred"]
            state.lead_days += result["lead_days_added"]
            state.carbon += result["carbon_added"]
            
            # Arbitrary logic: Add evenly to all inventory as generic purchase
            state.inventory["steel"] += 1.0
            state.inventory["chips"] += 1.0
            state.inventory["fabric"] += 1.0

    elif action == 1:  # approve_fastest
        result["action_label"] = "approve_fastest"
        if valid_suppliers:
            supplier = min(valid_suppliers, key=lambda x: x["lead_days"])
            result["selected_supplier"] = supplier
            
            result["cost_incurred"] = float(supplier["price_usd"])
            result["lead_days_added"] = int(supplier["lead_days"])
            result["carbon_added"] = float(supplier["carbon_tons"])
            
            state.budget -= result["cost_incurred"]
            state.lead_days += result["lead_days_added"]
            state.carbon += result["carbon_added"]
            
            state.inventory["steel"] += 1.0
            state.inventory["chips"] += 1.0
            state.inventory["fabric"] += 1.0

    elif action == 2:  # approve_greenest
        result["action_label"] = "approve_greenest"
        if valid_suppliers:
            supplier = min(valid_suppliers, key=lambda x: x["carbon_tons"])
            result["selected_supplier"] = supplier
            
            result["cost_incurred"] = float(supplier["price_usd"])
            result["lead_days_added"] = int(supplier["lead_days"])
            result["carbon_added"] = float(supplier["carbon_tons"])
            
            state.budget -= result["cost_incurred"]
            state.lead_days += result["lead_days_added"]
            state.carbon += result["carbon_added"]
            
            state.inventory["steel"] += 1.0
            state.inventory["chips"] += 1.0
            state.inventory["fabric"] += 1.0

    elif action == 3:  # reject_all
        result["action_label"] = "reject_all"
        penalty = 500.0
        result["cost_incurred"] = penalty
        state.budget -= penalty

    elif action == 4:  # negotiate_price
        result["action_label"] = "negotiate_price"
        if valid_suppliers:
            supplier = min(valid_suppliers, key=lambda x: x["price_usd"])
            # Create a shallow copy and apply a 10% discount
            discounted_supplier = supplier.copy()
            discounted_price = float(discounted_supplier["price_usd"]) * 0.90
            discounted_supplier["price_usd"] = discounted_price
            
            result["selected_supplier"] = discounted_supplier
            result["cost_incurred"] = discounted_price
            result["lead_days_added"] = int(discounted_supplier["lead_days"])
            result["carbon_added"] = float(discounted_supplier["carbon_tons"])
            
            state.budget -= result["cost_incurred"]
            state.lead_days += result["lead_days_added"]
            state.carbon += result["carbon_added"]
            
            state.inventory["steel"] += 1.0
            state.inventory["chips"] += 1.0
            state.inventory["fabric"] += 1.0

    elif action == 5:  # split_order
        result["action_label"] = "split_order"
        if len(valid_suppliers) >= 2:
            sorted_suppliers = sorted(valid_suppliers, key=lambda x: x["price_usd"])
            s1 = sorted_suppliers[0]
            s2 = sorted_suppliers[1]
            
            avg_price = (s1["price_usd"] + s2["price_usd"]) / 2.0
            max_lead = max(s1["lead_days"], s2["lead_days"])
            avg_carbon = (s1["carbon_tons"] + s2["carbon_tons"]) / 2.0
            
            # Provide a dummy supplier dictionary containing aggregate specs
            split_supplier = {
                "id": f"{s1['id']}-{s2['id']}-split",
                "country": s1["country"],
                "price_usd": avg_price,
                "lead_days": max_lead,
                "carbon_tons": avg_carbon,
                "available": True,
                "sanctioned_category": s1.get("sanctioned_category") # simplification
            }
            
            result["selected_supplier"] = split_supplier
            result["cost_incurred"] = float(avg_price)
            result["lead_days_added"] = int(max_lead)
            result["carbon_added"] = float(avg_carbon)
            
            state.budget -= result["cost_incurred"]
            state.lead_days += result["lead_days_added"]
            state.carbon += result["carbon_added"]

            state.inventory["steel"] += 1.0
            state.inventory["chips"] += 1.0
            state.inventory["fabric"] += 1.0

    elif action == 6:  # escalate
        result["action_label"] = "escalate"
        penalty = 200.0  # soft penalty for manual escalation
        result["cost_incurred"] = penalty
        state.budget -= penalty

    # Advance the step count once per action
    state.step_count += 1
    
    return result
