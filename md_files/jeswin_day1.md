# Jeswin (P2) — Day 1 Instructions
**Role:** Data & Tasks | **Theme:** Build all JSON data files that power the simulation rules

> ⚠️ **Today's Critical Gate:** All JSON files must be valid JSON (parseable with `json.load()`), and every field name must exactly match the `SupplyChainState` fields that Jenish shares with the team by end of day.

---

## 🔗 Cross-Team Dependency Note

Today you work **independently on file content**, but at the end of the day you have a critical synchronisation point with Jenish. He will share his `SupplyChainState` field names and the field names his `constraint_engine.py` expects from your JSON files. **You must verify your field names match his exactly.** A mismatch like `carbon_levy` vs `carbon_levy_per_ton_usd` will cause a silent bug — the code won't crash, it'll just use `None` everywhere, producing wrong results. Fix all mismatches before the end-of-day sync concludes.

---

## Phase 1 — Write the India Policy (`policies/india_policy.json`)

**What you're building:** A JSON rulebook that encodes Indian trade law for the simulation. Jenish's `constraint_engine.py` will load this file and use it to validate every procurement action the agent takes involving Indian suppliers.

Think of each field as a switch or dial that the rule engine reads. Some rules are absolute ("hard rules" — breaking them ends the episode immediately), and some are nudges ("soft rules" — breaking them reduces the reward but the simulation continues).

```json
{
    "country": "India",
    "import_duty_rate": 0.18,
    "gst_rate": 0.12,
    "carbon_levy_per_ton_usd": 15.0,
    "max_single_source_usd": 50000,
    "mandatory_local_content_pct": 0.30,
    "sanctioned_categories": ["chinese_military_linked", "iran_linked"],
    "hard_rules": ["no_sanctioned_supplier", "local_content_minimum"],
    "soft_rules": ["prefer_low_carbon", "prefer_domestic_supplier"]
}
```

**What each field means in context:**
- `import_duty_rate: 0.18` — When the agent buys from an Indian supplier, 18% gets added to the cost on top of the supplier's listed price. This directly affects the cost efficiency component of the reward.
- `gst_rate: 0.12` — An additional 12% goods and services tax. Combined with import duty, Indian purchases carry a 30% total tax overhead — making Indian suppliers not always the cheapest despite often having the lowest base price.
- `carbon_levy_per_ton_usd: 15.0` — India charges $15 per ton of carbon. This is much lower than the EU ($85/ton), so Indian suppliers are relatively carbon-penalty-friendly.
- `max_single_source_usd: 50000` — The agent cannot spend more than $50,000 with a single Indian supplier in one order. Exceeding this is a **hard rule violation** — episode ends immediately.
- `mandatory_local_content_pct: 0.30` — At least 30% of the total order value must come from Indian-origin suppliers. Violating this is a hard rule.
- `sanctioned_categories` — Any supplier tagged with these categories is completely off-limits. This is always a hard rule.

### ✅ Pitstop Audit — Phase 1

```python
import json

with open("policies/india_policy.json", "r") as f:
    policy = json.load(f)

# Validate all required fields exist
required = ["country", "import_duty_rate", "gst_rate", "carbon_levy_per_ton_usd",
            "max_single_source_usd", "mandatory_local_content_pct",
            "sanctioned_categories", "hard_rules", "soft_rules"]

for field in required:
    assert field in policy, f"Missing field: {field}"

assert isinstance(policy["hard_rules"], list), "hard_rules must be a list"
assert isinstance(policy["sanctioned_categories"], list), "sanctioned_categories must be a list"
print("✅ India policy is valid JSON with all required fields")
```
**All assertions pass → Phase 1 complete.**

---

## Phase 2 — Write the EU Policy (`policies/eu_policy.json`)

**What you're building:** The European Union's rulebook. The EU has the strictest carbon rules by far — a levy of $85 per tonne compared to India's $15. It also has a hard cap on how many carbon tons a single order can produce. This makes the EU a high-quality, low-carbon option, but environmentally bad orders from EU suppliers will be severely penalised.

```json
{
    "country": "EU",
    "import_duty_rate": 0.05,
    "carbon_levy_per_ton_usd": 85.0,
    "max_carbon_tons_per_order": 3.0,
    "deforestation_act_applies": true,
    "gdpr_data_flag": true,
    "sanctioned_categories": ["russia_linked", "belarus_linked"],
    "hard_rules": ["no_sanctioned_supplier", "carbon_limit_per_order"],
    "soft_rules": ["prefer_certified_green", "prefer_eu_supplier"]
}
```

**Key differences from India to understand:**
- `carbon_levy_per_ton_usd: 85.0` — This is the EU's Carbon Border Adjustment Mechanism. At $85/ton, even a moderately carbon-heavy EU supplier can be more expensive than its listed price suggests. The AI agent will need to learn to avoid high-carbon EU suppliers.
- `max_carbon_tons_per_order: 3.0` — This is a hard limit. Any single order from an EU supplier that produces more than 3 tons of carbon is an immediate hard violation. The constraint engine will check this per-order, not cumulatively.
- `deforestation_act_applies: true` — The EU Deforestation Regulation (EUDR) means suppliers linked to deforestation are banned. In `suppliers.json`, you can flag specific EU suppliers with `"deforestation_risk": true` and the constraint engine will treat them as sanctioned under this rule.

### ✅ Pitstop Audit — Phase 2

```python
with open("policies/eu_policy.json", "r") as f:
    eu = json.load(f)

assert eu["carbon_levy_per_ton_usd"] == 85.0, "EU carbon levy must be 85.0"
assert eu["max_carbon_tons_per_order"] == 3.0, "EU max carbon per order must be 3.0"
assert "carbon_limit_per_order" in eu["hard_rules"], "carbon_limit must be a hard rule"
assert isinstance(eu["deforestation_act_applies"], bool), "deforestation flag must be boolean"
print("✅ EU policy valid")
```
**All assertions pass → Phase 2 complete.**

---

## Phase 3 — Write the USA Policy (`policies/usa_policy.json`)

**What you're building:** The United States rulebook. The USA has the most geopolitically complex rules — OFAC sanctions (banned countries for financial transactions) and a "Buy American" requirement that kicks in above a spending threshold. The OFAC list (Iran, North Korea, Russia) creates absolute hard stops that the agent must learn to avoid entirely.

```json
{
    "country": "USA",
    "import_duty_rate": 0.08,
    "carbon_levy_per_ton_usd": 0.0,
    "buy_american_threshold_usd": 100000,
    "buy_american_domestic_pct": 0.50,
    "ofac_sanctioned_countries": ["Iran", "North Korea", "Russia"],
    "export_control_applies": true,
    "sanctioned_categories": ["iran_linked", "north_korea_linked", "russia_linked"],
    "hard_rules": ["no_ofac_country", "buy_american_above_threshold"],
    "soft_rules": ["prefer_domestic_supplier", "prefer_low_carbon"]
}
```

**Key points to understand:**
- `carbon_levy_per_ton_usd: 0.0` — The USA does not currently have a federal carbon pricing mechanism, so this is zero. This makes US suppliers the most carbon-cost-neutral option from a policy standpoint, even if their physical emissions are high.
- `buy_american_threshold_usd: 100000` — Only when total procurement in an episode exceeds $100,000 does the "Buy American" rule activate. Below that threshold, you can buy from anywhere.
- `buy_american_domestic_pct: 0.50` — Above the threshold, at least 50% of total spend must go to US-origin suppliers. This is a hard rule, so violating it ends the episode.
- `ofac_sanctioned_countries` — Unlike the other countries' `sanctioned_categories` (which describe supplier types), this list directly names countries. Any supplier whose `country` field appears in this list is permanently off-limits.

### ✅ Pitstop Audit — Phase 3

```python
with open("policies/usa_policy.json", "r") as f:
    usa = json.load(f)

assert "Iran" in usa["ofac_sanctioned_countries"], "Iran must be in OFAC list"
assert "no_ofac_country" in usa["hard_rules"], "OFAC check must be a hard rule"
assert usa["buy_american_domestic_pct"] == 0.50, "Buy American must be 50%"
assert usa["carbon_levy_per_ton_usd"] == 0.0, "USA has no carbon levy"
print("✅ USA policy valid")
```
**All assertions pass → Phase 3 complete.**

---

## Phase 4 — Write the Suppliers Dataset (`data/suppliers.json`)

**What you're building:** The complete list of all 10 suppliers the AI agent can potentially buy from. This is the "marketplace" of the simulation. Each supplier has attributes that directly feed into the agent's observations and the reward formula.

The distribution must be: **4 India suppliers**, **3 EU suppliers**, **3 USA suppliers**.

```json
[
    {"id": "IN_01", "name": "Mumbai Steel Co", "country": "India",
     "price_usd": 38000, "lead_days": 7, "carbon_tons": 3.5, "available": true,
     "sanctioned_category": null},

    {"id": "IN_02", "name": "Chennai Chips Ltd", "country": "India",
     "price_usd": 42000, "lead_days": 5, "carbon_tons": 2.8, "available": true,
     "sanctioned_category": null},

    {"id": "IN_03", "name": "Delhi Fabrics", "country": "India",
     "price_usd": 35000, "lead_days": 10, "carbon_tons": 4.0, "available": true,
     "sanctioned_category": null},

    {"id": "IN_04", "name": "Pune Components", "country": "India",
     "price_usd": 50000, "lead_days": 4, "carbon_tons": 1.9, "available": true,
     "sanctioned_category": null},

    {"id": "EU_01", "name": "Berlin Precision GmbH", "country": "EU",
     "price_usd": 65000, "lead_days": 3, "carbon_tons": 1.2, "available": true,
     "sanctioned_category": null},

    {"id": "EU_02", "name": "Lyon Textile SA", "country": "EU",
     "price_usd": 72000, "lead_days": 4, "carbon_tons": 0.8, "available": true,
     "sanctioned_category": null},

    {"id": "FR_01", "name": "Paris AutoParts", "country": "EU",
     "price_usd": 68000, "lead_days": 5, "carbon_tons": 1.5, "available": true,
     "sanctioned_category": null},

    {"id": "US_01", "name": "Texas Steel Corp", "country": "USA",
     "price_usd": 55000, "lead_days": 6, "carbon_tons": 2.2, "available": true,
     "sanctioned_category": null},

    {"id": "US_02", "name": "Silicon Valley Chips", "country": "USA",
     "price_usd": 80000, "lead_days": 2, "carbon_tons": 0.5, "available": true,
     "sanctioned_category": null},

    {"id": "US_03", "name": "NYC Fabrics Inc", "country": "USA",
     "price_usd": 62000, "lead_days": 8, "carbon_tons": 1.8, "available": true,
     "sanctioned_category": null}
]
```

**Design note:** The suppliers are intentionally designed with trade-offs. `US_02` is the fastest and lowest-carbon option but the most expensive. `IN_01` is the cheapest but has high carbon and long lead times. `EU_01` is balanced but carries the EU carbon levy. This creates a genuinely difficult decision space for the AI agent — there is no single "best" supplier, which makes the training problem interesting.

### ✅ Pitstop Audit — Phase 4

```python
import json

with open("data/suppliers.json", "r") as f:
    suppliers = json.load(f)

india = [s for s in suppliers if s["country"] == "India"]
eu    = [s for s in suppliers if s["country"] == "EU"]
usa   = [s for s in suppliers if s["country"] == "USA"]

assert len(suppliers) == 10, f"Expected 10 suppliers, got {len(suppliers)}"
assert len(india) == 4, f"Expected 4 India suppliers, got {len(india)}"
assert len(eu) == 3, f"Expected 3 EU suppliers, got {len(eu)}"
assert len(usa) == 3, f"Expected 3 USA suppliers, got {len(usa)}"

# Check all required fields exist on every supplier
required_fields = ["id", "name", "country", "price_usd", "lead_days", "carbon_tons", "available"]
for s in suppliers:
    for field in required_fields:
        assert field in s, f"Supplier {s.get('id','?')} missing field: {field}"

print("✅ suppliers.json valid — 10 suppliers, all fields present")
```
**All assertions pass → Phase 4 complete.**

---

## Phase 5 — Write the Disruption Scenarios (`disruptions/scenarios.json`)

**What you're building:** The three crisis events that fire automatically at pre-set step numbers. These are seeded — meaning with the same random seed, the same disruption always fires at the same step number. This reproducibility is essential for fair judging.

```json
[
    {
        "name": "port_strike_india",
        "trigger_step": 8,
        "min_task": 2,
        "duration_steps": 5,
        "affected_suppliers": ["IN_02", "IN_03"],
        "effect": "unavailable",
        "description": "Mumbai port strike — IN_02 and IN_03 cannot fulfill orders"
    },
    {
        "name": "war_reroute_eu",
        "trigger_step": 15,
        "min_task": 3,
        "duration_steps": 10,
        "affected_suppliers": ["EU_01", "EU_02", "FR_01"],
        "effect": "lead_time_multiplier",
        "multiplier": 2.5,
        "description": "EU-India east route blocked — all EU lead times ×2.5"
    },
    {
        "name": "protest_france",
        "trigger_step": 22,
        "min_task": 3,
        "duration_steps": 3,
        "affected_suppliers": ["FR_01"],
        "effect": "lead_time_add",
        "days_added": 14,
        "description": "French transport strike — FR_01 gets +14 day delay"
    }
]
```

**Understanding `min_task`:** This field tells the disruption engine which tasks the disruption applies to. `min_task: 2` means the port strike fires in Task 2 and Task 3, but not Task 1 (since Task 1 is the easy mode with no disruptions). `min_task: 3` means the war reroute and France protest only fire in Task 3.

### ✅ Pitstop Audit — Phase 5

```python
with open("disruptions/scenarios.json", "r") as f:
    scenarios = json.load(f)

assert len(scenarios) == 3, "Must have exactly 3 disruption scenarios"
trigger_steps = [s["trigger_step"] for s in scenarios]
assert 8 in trigger_steps, "Port strike must trigger at step 8"
assert 15 in trigger_steps, "War reroute must trigger at step 15"
assert 22 in trigger_steps, "France protest must trigger at step 22"

for s in scenarios:
    assert "name" in s and "trigger_step" in s and "affected_suppliers" in s
    print(f"  ✓ {s['name']} at step {s['trigger_step']}")

print("✅ disruptions/scenarios.json valid")
```
**All 3 disruptions present at correct steps → Phase 5 complete.**

---

## 📤 End-of-Day Sync (Mandatory)

When Jenish shares his `SupplyChainState` field names, go through this checklist line by line:

Your JSON field `carbon_tons` (in `suppliers.json`) must match whatever Jenish calls the carbon accumulator in `SupplyChainState`. If he calls it `carbon_footprint`, your field must be `carbon_footprint`. If there is any mismatch → fix your JSON files right now, before the sync call ends.

Check that `hard_rules` and `soft_rules` in your policy JSONs use the exact same string values that Jenish's `constraint_engine.py` checks for. If his engine checks `if "no_sanctioned_supplier" in policy["hard_rules"]`, your JSON must have exactly `"no_sanctioned_supplier"` — not `"no_sanctioned"` or `"sanctioned_supplier_check"`.
