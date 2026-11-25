"""
Export POIs and sample scenarios from the cached taoist/TRACE dataset
Saves to data/trace_pois.json and data/trace_scenarios.json
"""

import json
import os
from datasets import load_dataset

def export_trace():
    print("Loading taoist/TRACE dataset...")
    # Load with local cache
    ds = load_dataset("taoist/TRACE")
    
    # 1. Extract Unique POIs
    pois_by_id = {}
    for split_name in ["train", "validation", "test"]:
        if split_name not in ds:
            continue
        for row in ds[split_name]:
            city = row.get("city", "")
            for p in row.get("referenced_pois", []):
                bid = p.get("business_id")
                if not bid:
                    continue
                if bid not in pois_by_id:
                    pois_by_id[bid] = {
                        "business_id": bid,
                        "name": p.get("name", ""),
                        "city": city,
                        "poi_type": p.get("poi_type", "attraction"),
                        "stars": float(p.get("stars", 4.0) or 4.0),
                        "categories": ", ".join(p.get("categories", [])),
                        "address": p.get("address", ""),
                        "price_range": p.get("price_range", ""),
                    }

    os.makedirs("data", exist_ok=True)
    pois_list = list(pois_by_id.values())
    with open("data/trace_pois.json", "w", encoding="utf-8") as f:
        json.dump(pois_list, f, indent=2)
    print(f"Exported {len(pois_list)} POIs to data/trace_pois.json")

    # 2. Extract Sample Scenarios for Chatbot / AI Travel Inspiration
    scenarios = []
    seen_personas = set()
    for row in ds["train"]:
        scenario = row.get("scenario", {})
        p_type = scenario.get("persona_type", "")
        city = row.get("city", "")
        key = (city, p_type)
        if key not in seen_personas and len(scenarios) < 30:
            seen_personas.add(key)
            # Get first user query
            first_user_turn = ""
            for turn in row.get("turns", []):
                if turn.get("role") == "user":
                    first_user_turn = turn.get("text", "")
                    break
            scenarios.append({
                "city": city,
                "persona_type": p_type,
                "persona_description": scenario.get("persona_description", ""),
                "travel_context": scenario.get("travel_context", ""),
                "sample_query": first_user_turn,
            })

    with open("data/trace_scenarios.json", "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)
    print(f"Exported {len(scenarios)} sample travel scenarios to data/trace_scenarios.json")

if __name__ == "__main__":
    export_trace()
