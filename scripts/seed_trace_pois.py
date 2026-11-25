"""
Seed PointOfInterest records from data/trace_pois.json into SQLite
"""

import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Destination, PointOfInterest

def seed_pois():
    app = create_app()
    with app.app_context():
        # Ensure points_of_interest table exists
        db.create_all()

        json_path = os.path.join(app.root_path, "data", "trace_pois.json")
        if not os.path.exists(json_path):
            print("trace_pois.json not found!")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            pois_data = json.load(f)

        print(f"Loaded {len(pois_data)} POIs from JSON.")

        # Map cities to destination IDs
        destinations = Destination.query.all()
        dest_map = {}
        for d in destinations:
            dest_map[d.name.lower()] = d.id
            if d.city:
                dest_map[d.city.lower()] = d.id

        existing_bids = {p.business_id for p in PointOfInterest.query.all() if p.business_id}
        print(f"Existing POIs in DB: {len(existing_bids)}")

        new_pois = []
        for p in pois_data:
            bid = p.get("business_id")
            if bid in existing_bids:
                continue
            city = p.get("city", "")
            city_lower = city.lower()
            
            # Match destination
            dest_id = dest_map.get(city_lower)

            poi = PointOfInterest(
                destination_id=dest_id,
                name=p.get("name", "Unknown Spot"),
                city=city,
                poi_type=p.get("poi_type", "attraction"),
                stars=p.get("stars", 4.0),
                categories=p.get("categories", ""),
                address=p.get("address", ""),
                price_range=p.get("price_range", "$$"),
                business_id=bid,
            )
            new_pois.append(poi)

        print(f"Adding {len(new_pois)} new POIs to DB...")
        batch_size = 150
        for i in range(0, len(new_pois), batch_size):
            db.session.add_all(new_pois[i:i + batch_size])
            db.session.commit()

        total = PointOfInterest.query.count()
        matched = PointOfInterest.query.filter(PointOfInterest.destination_id.isnot(None)).count()
        print(f"🎉 Total POIs in DB: {total} (Linked to destinations: {matched})")

if __name__ == "__main__":
    seed_pois()
