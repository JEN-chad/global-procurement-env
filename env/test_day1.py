# test_day1.py — run this as: python test_day1.py
from supply_chain_sim import SupplyChainState, apply_action
from constraint_engine import load_policy, validate_action

state = SupplyChainState(budget=200000.0)
policy = load_policy("India")  # uses your stub JSON

mock_suppliers = [
    {"id": "IN_01", "country": "India", "price_usd": 40000, "lead_days": 5, "carbon_tons": 2.0, "available": True},
]

# Simulate 5 steps
for i in range(5):
    result = apply_action(state, 0, mock_suppliers)
    is_valid, penalty, vtype = validate_action(state, result["selected_supplier"], policy)
    print(f"Step {state.step_count}: budget={state.budget:.0f}, valid={is_valid}, penalty={penalty}")

print("✅ 5 steps completed without crash")
