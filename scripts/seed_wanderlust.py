"""
Seed Wanderlust destinations & POIs into the SQLite database.
Enriches existing destinations with new descriptions, vibe tags, and personas.
Adds 23K+ POIs from the wanderlust-ai-dataset.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Destination, PointOfInterest

# Map wanderlust categories to our DB categories
CATEGORY_MAP = {
    "beach": "Beach",
    "mountain": "Mountain",
    "city": "City",
    "cultural": "Cultural",
    "historical": "Historical",
    "nature": "Nature",
    "romantic": "Romantic",
    "adventure": "Adventure",
    "coastal": "Coastal",
    "urban": "City",
    "rural": "Nature",
    "island": "Beach",
    "desert": "Adventure",
    "tropical": "Beach",
    "arctic": "Adventure",
}

# Map wanderlust POI categories to our poi_type
POI_TYPE_MAP = {
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "bar": "restaurant",
    "food": "restaurant",
    "street food": "restaurant",
    "bakery": "restaurant",
    "hotel": "hotel",
    "hostel": "hotel",
    "resort": "hotel",
    "accommodation": "hotel",
    "lodge": "hotel",
    "guesthouse": "hotel",
    "boutique hotel": "hotel",
    "museum": "attraction",
    "temple": "attraction",
    "park": "attraction",
    "beach": "attraction",
    "market": "attraction",
    "landmark": "attraction",
    "monument": "attraction",
    "gallery": "attraction",
    "theater": "attraction",
    "church": "attraction",
    "mosque": "attraction",
    "garden": "attraction",
    "nightlife": "attraction",
    "shopping": "attraction",
    "spa": "attraction",
    "viewpoint": "attraction",
    "waterfall": "attraction",
    "trail": "attraction",
    "wine": "restaurant",
    "brewery": "restaurant",
    "rooftop bar": "restaurant",
}


def seed_wanderlust():
    app = create_app()
    with app.app_context():
        db.create_all()

        # --- 1. Enrich destinations from wanderlust_destinations ---
        dest_path = os.path.join(app.root_path, "data", "wanderlust_destinations_train.json")
        if os.path.exists(dest_path):
            with open(dest_path, "r", encoding="utf-8") as f:
                wl_dests = json.load(f)
            print(f"Loaded {len(wl_dests)} wanderlust destination records.")

            # Build lookup for existing destinations
            existing = {}
            for d in Destination.query.all():
                existing[d.name.lower()] = d
                if d.city:
                    existing[d.city.lower()] = d

            enriched = 0
            for wd in wl_dests:
                city = (wd.get("city") or "").strip()
                if not city:
                    continue
                key = city.lower()
                dest = existing.get(key)
                if dest:
                    # Enrich with better description if current is generic
                    wl_desc = (wd.get("description") or "").strip()
                    if wl_desc and len(wl_desc) > len(dest.description or ""):
                        dest.description = wl_desc[:500]
                        enriched += 1
            db.session.commit()
            print(f"Enriched {enriched} existing destinations with Wanderlust descriptions.")
        else:
            print("wanderlust_destinations_train.json not found, skipping destination enrichment.")

        # --- 2. Seed POIs from wanderlust_pois ---
        pois_path = os.path.join(app.root_path, "data", "wanderlust_pois_train.json")
        if os.path.exists(pois_path):
            with open(pois_path, "r", encoding="utf-8") as f:
                wl_pois = json.load(f)
            print(f"Loaded {len(wl_pois)} wanderlust POI records.")

            # Build destination ID lookup
            dest_map = {}
            for d in Destination.query.all():
                dest_map[d.name.lower()] = d.id
                if d.city:
                    dest_map[d.city.lower()] = d.id

            # Get existing POI names per city to avoid duplicates
            existing_pois = set()
            for p in PointOfInterest.query.with_entities(PointOfInterest.name, PointOfInterest.city).all():
                existing_pois.add((p.name.lower(), (p.city or "").lower()))

            new_pois = []
            for wp in wl_pois:
                name = (wp.get("name") or "").strip()
                city = (wp.get("city") or "").strip()
                if not name or not city:
                    continue

                dedupe_key = (name.lower(), city.lower())
                if dedupe_key in existing_pois:
                    continue
                existing_pois.add(dedupe_key)

                raw_cat = (wp.get("category") or "attraction").strip().lower()
                poi_type = POI_TYPE_MAP.get(raw_cat, "attraction")
                dest_id = dest_map.get(city.lower())
                desc = (wp.get("description") or "").strip()

                poi = PointOfInterest(
                    destination_id=dest_id,
                    name=name,
                    city=city,
                    poi_type=poi_type,
                    stars=4.0,
                    categories=raw_cat.title(),
                    address="",
                    price_range="",
                    business_id="",
                )
                new_pois.append(poi)

            print(f"Adding {len(new_pois)} new Wanderlust POIs to DB...")
            batch = 200
            for i in range(0, len(new_pois), batch):
                db.session.add_all(new_pois[i:i + batch])
                db.session.commit()

            total = PointOfInterest.query.count()
            linked = PointOfInterest.query.filter(PointOfInterest.destination_id.isnot(None)).count()
            print(f"Done! Total POIs in DB: {total} (Linked to destinations: {linked})")
        else:
            print("wanderlust_pois_train.json not found, skipping POI seeding.")


if __name__ == "__main__":
    seed_wanderlust()
