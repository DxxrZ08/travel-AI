"""
Seed Destinations & Trips Dataset into SQLite Database
Reads raw data from data/world_destinations_raw.txt and data/user_trips_dataset.csv
"""

import os
import re
import csv
import random
import hashlib
from app import create_app
from models import db, Destination, Trip, User

# Iconic destination curated images and highlights for top world hubs
CURATED_DATA = {
    "Paris": {
        "category": "Romantic",
        "description": "The City of Light captivates with world-class art, timeless architecture, world-renowned bakeries, and romantic boulevards along the Seine.",
        "highlights": "Eiffel Tower, Louvre Museum, Notre-Dame, Montmartre",
        "image_url": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to June, September to November",
    },
    "Tokyo": {
        "category": "City",
        "description": "A dazzling collision of ultra-modern skyscrapers, ancient Shinto shrines, neon nightlife, and unmatched culinary artistry.",
        "highlights": "Shibuya Crossing, Senso-ji Temple, Meiji Shrine, Akihabara",
        "image_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "March to May, September to November",
    },
    "London": {
        "category": "Cultural",
        "description": "Rich royal history meets contemporary culture, royal parks, grand museums, and lively Thames-side neighborhoods.",
        "highlights": "Big Ben, Tower of London, British Museum, London Eye",
        "image_url": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "May to September",
    },
    "New York": {
        "category": "City",
        "description": "The city that never sleeps offers Broadway shows, world-famous skylines, Central Park strolls, and neighborhood dining from every culture.",
        "highlights": "Times Square, Central Park, Empire State Building, Brooklyn Bridge",
        "image_url": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to June, September to November",
    },
    "New York City": {
        "category": "City",
        "description": "The city that never sleeps offers Broadway shows, world-famous skylines, Central Park strolls, and neighborhood dining from every culture.",
        "highlights": "Times Square, Central Park, Empire State Building, Brooklyn Bridge",
        "image_url": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to June, September to November",
    },
    "Rome": {
        "category": "Historical",
        "description": "An open-air museum filled with millennia of history, ancient ruins, Renaissance basilicas, and delicious Roman pasta.",
        "highlights": "Colosseum, Vatican Museums, Trevi Fountain, Pantheon",
        "image_url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to May, September to October",
    },
    "Bali": {
        "category": "Beach",
        "description": "Island of the Gods boasting sacred cliffside temples, terraced rice paddies, serene yoga retreats, and premier surf breaks.",
        "highlights": "Ubud Rice Terraces, Uluwatu Temple, Tanah Lot, Seminyak Beach",
        "image_url": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to October",
    },
    "Kyoto": {
        "category": "Cultural",
        "description": "Temple paths, bamboo groves, traditional geisha districts, and serene Zen rock gardens make Kyoto Japan's cultural heart.",
        "highlights": "Fushimi Inari Shrine, Arashiyama Bamboo Grove, Kinkaku-ji, Gion",
        "image_url": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "March to May, October to November",
    },
    "Dubai": {
        "category": "City",
        "description": "Futuristic skyline rising from the desert, ultra-luxury shopping, golden dunes safaris, and daring architectural wonders.",
        "highlights": "Burj Khalifa, Dubai Mall, Palm Jumeirah, Desert Safari",
        "image_url": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "November to March",
    },
    "Barcelona": {
        "category": "Cultural",
        "description": "Gaudí's fantastical architectural masterworks, sunny Mediterranean beaches, Gothic quarters, and world-class tapas bars.",
        "highlights": "Sagrada Família, Park Güell, Las Ramblas, Gothic Quarter",
        "image_url": "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "May to June, September to October",
    },
    "Sydney": {
        "category": "Coastal",
        "description": "Dramatic harbor views, world-famous golden surf beaches, architectural icons, and vibrant waterside dining.",
        "highlights": "Sydney Opera House, Harbor Bridge, Bondi Beach, Manly Ferry",
        "image_url": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "September to November, March to May",
    },
    "Rio de Janeiro": {
        "category": "Beach",
        "description": "Surrounded by lush granite peaks and shimmering Atlantic bays, Rio bursts with samba rhythms and legendary beach culture.",
        "highlights": "Christ the Redeemer, Sugarloaf Mountain, Copacabana Beach, Ipanema",
        "image_url": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "December to March",
    },
    "Amsterdam": {
        "category": "Cultural",
        "description": "Picturesque canal rings lined with gabled townhouses, legendary museums, cycling culture, and open-minded cafes.",
        "highlights": "Rijksmuseum, Van Gogh Museum, Anne Frank House, Jordaan Canals",
        "image_url": "https://images.unsplash.com/photo-1512470876302-972faa2aa9a4?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to May, September to November",
    },
    "Bangkok": {
        "category": "Cultural",
        "description": "Intricate gilded temples, bustling boat-filled canals, world-renowned street food stalls, and sensory night markets.",
        "highlights": "Grand Palace, Wat Arun, Chatuchak Market, Chao Phraya River",
        "image_url": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "November to February",
    },
    "Phuket": {
        "category": "Beach",
        "description": "Thailand's largest island offers turquoise Andaman waters, dramatic limestone karsts, lively night markets, and island hopping.",
        "highlights": "Patong Beach, Big Buddha, Phi Phi Islands tour, Old Phuket Town",
        "image_url": "https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "November to April",
    },
    "Cancun": {
        "category": "Beach",
        "description": "Gateway to the Mayan Riviera with powder-soft white sand beaches, crystalline Caribbean water, and nearby ancient ruins.",
        "highlights": "Hotel Zone Beaches, Isla Mujeres, Chichen Itza Day Trip, Cenotes",
        "image_url": "https://images.unsplash.com/photo-1510097467424-192d713fd8b2?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "December to April",
    },
    "Santorini": {
        "category": "Romantic",
        "description": "Iconic whitewashed caldera villages clinging to volcanic cliffs above the deep blue Aegean with legendary sunset vistas.",
        "highlights": "Oia Sunset, Fira Caldera Walk, Red Beach, Akrotiri Ruins",
        "image_url": "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "May to October",
    },
    "Cairo": {
        "category": "Historical",
        "description": "The grand historic cradle on the Nile boasting the Great Pyramids of Giza, the Sphinx, and vibrant historic bazaars.",
        "highlights": "Giza Pyramids, The Sphinx, Grand Egyptian Museum, Khan el-Khalili",
        "image_url": "https://images.unsplash.com/photo-1572252009286-268acec5ca0a?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "October to April",
    },
    "Cape Town": {
        "category": "Nature",
        "description": "Where Table Mountain meets two oceans — featuring coastal drives, penguin colonies, vineyards, and rich coastal history.",
        "highlights": "Table Mountain Cableway, Cape Point, Boulders Beach, V&A Waterfront",
        "image_url": "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "October to April",
    },
    "Minsk": {
        "category": "Cultural",
        "description": "Belarus’s capital blends broad historic avenues, grand civic architecture, leafy parks, and lively cafés around the Svislach River.",
        "highlights": "Independence Square, Trinity Hill, Victory Square, Great Patriotic War Museum",
        "image_url": "https://images.unsplash.com/photo-1731169921081-31d16a3ec92a?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "May to September",
    },
    "Jahorina": {
        "category": "Mountain",
        "description": "A Bosnian mountain resort known for forested slopes, alpine scenery, and year-round hiking and winter sports.",
        "highlights": "Jahorina Ski Resort, Olympic Center, mountain trails, panoramic viewpoints",
        "image_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "December to March (skiing), June to September (hiking)",
    },
    "Melbourne": {
        "category": "City",
        "description": "Australia’s cultural capital pairs a lively arts scene with laneway cafés, distinctive architecture, gardens, and a celebrated waterfront.",
        "highlights": "Federation Square, Royal Botanic Gardens, Queen Victoria Market, Yarra River",
        "image_url": "https://images.unsplash.com/photo-1595434971780-79d5c20c5090?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "March to May, September to November",
    },
    "Zillertal": {
        "category": "Mountain",
        "description": "An Austrian alpine valley of high peaks, mountain villages, scenic lifts, hiking trails, and year-round outdoor activities.",
        "highlights": "Hintertux Glacier, Zillertal High Road, Mayrhofen, alpine hiking trails",
        "image_url": "https://images.unsplash.com/photo-1648147385426-68b1736c7d8f?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "December to March (skiing), June to September (hiking)",
    },
    "Yerevan": {
        "category": "Cultural",
        "description": "Armenia’s capital is known for rose-colored tuff architecture, lively public squares, museums, and views toward Mount Ararat.",
        "highlights": "Republic Square, Cascade Complex, Matenadaran, Vernissage Market",
        "image_url": "https://images.unsplash.com/photo-1660720212485-9d18192c4c8a?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "April to June, September to October",
    },
    "Uyuni": {
        "category": "Nature",
        "description": "A gateway to Bolivia’s immense salt flats, high-altitude lagoons, volcanic landscapes, and surreal Andean horizons.",
        "highlights": "Salar de Uyuni, Incahuasi Island, Train Cemetery, Eduardo Avaroa Reserve",
        "image_url": "https://images.unsplash.com/photo-1641755222059-8086a4f8c850?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "May to November (dry season), January to March (mirror effect)",
    },
    "Butrint": {
        "category": "Historical",
        "description": "A UNESCO-listed archaeological park where Greek, Roman, Byzantine, and Venetian remains sit among wetlands and woodland in southern Albania.",
        "highlights": "Ancient Theatre, Venetian Tower, Baptistery, Lake Butrint",
        "image_url": "https://images.unsplash.com/photo-1741267087486-ca82e9fde5d7?w=1000&auto=format&fit=crop&q=85",
        "is_featured": False,
        "best_time": "April to June, September to October",
    },
    "Vancouver": {
        "category": "Nature",
        "description": "Seaport surrounded by coastal mountains, ancient temperate rainforests, scenic sea walls, and diverse food neighborhoods.",
        "highlights": "Stanley Park Seawall, Granville Island, Capilano Suspension Bridge, Gastown",
        "image_url": "https://images.unsplash.com/photo-1559511260-66a65e0982d5?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "May to September",
    },
    "Seoul": {
        "category": "City",
        "description": "High-tech metropolis where centuries-old royal palaces sit alongside neon K-pop districts, bustling night markets, and mountain trails.",
        "highlights": "Gyeongbokgung Palace, Bukchon Hanok Village, Myeongdong, N Seoul Tower",
        "image_url": "https://images.unsplash.com/photo-1538485399081-7191377e8241?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "March to May, September to November",
    },
    "Agra": {
        "category": "Historical",
        "description": "Home to the immortal white marble Taj Mahal, a world wonder along the Yamuna River rich with Mughal architectural majesty.",
        "highlights": "Taj Mahal, Agra Fort, Mehtab Bagh, Fatehpur Sikri",
        "image_url": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "October to March",
    },
    "Jaipur": {
        "category": "Cultural",
        "description": "Rajasthan's regal Pink City featuring imposing hilltop forts, ornate royal palaces, and vibrant handloom textile bazaars.",
        "highlights": "Amber Palace, Hawa Mahal, City Palace, Jal Mahal",
        "image_url": "https://images.unsplash.com/photo-1603262110263-fb010d6e59d4?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "October to March",
    },
    "Venice": {
        "category": "Romantic",
        "description": "The floating Byzantine masterpiece built across 100+ islands, connected by stone bridges, winding canals, and gondolas.",
        "highlights": "St. Mark's Basilica, Grand Canal Gondola, Rialto Bridge, Doge's Palace",
        "image_url": "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to June, September to October",
    },
    "Florence": {
        "category": "Cultural",
        "description": "Cradle of the Renaissance boasting the terracotta-tiled Duomo, Michelangelo's David, and the romantic Ponte Vecchio bridge.",
        "highlights": "Florence Cathedral (Duomo), Uffizi Gallery, Ponte Vecchio, Galleria dell'Accademia",
        "image_url": "https://images.unsplash.com/photo-1543429776-2782fc8e1acd?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to June, September to October",
    },
    "Vienna": {
        "category": "Cultural",
        "description": "Imperial capital celebrated for grand Habsburg palaces, classical music legacies of Mozart and Beethoven, and historic coffee houses.",
        "highlights": "Schönbrunn Palace, St. Stephen's Cathedral, Hofburg, Belvedere Palace",
        "image_url": "https://images.unsplash.com/photo-1516550893923-42d28e5677af?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to May, September to October",
    },
    "Prague": {
        "category": "Historical",
        "description": "The City of a Hundred Spires features the historic Charles Bridge, fairy-tale hilltop castle, and charming medieval Old Town.",
        "highlights": "Charles Bridge, Prague Castle, Old Town Astronomical Clock, St. Vitus Cathedral",
        "image_url": "https://images.unsplash.com/photo-1541849546-216549ae216d?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "May to September",
    },
    "San Francisco": {
        "category": "City",
        "description": "The hilly jewel of Northern California famous for the Golden Gate Bridge, historic cable cars, foggy bays, and Victorian architecture.",
        "highlights": "Golden Gate Bridge, Alcatraz Island, Fisherman's Wharf, Painted Ladies",
        "image_url": "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "September to November",
    },
    "Honolulu": {
        "category": "Beach",
        "description": "Hawaii's tropical capital with iconic crescent Waikiki Beach, Diamond Head crater hikes, and rich Polynesian island traditions.",
        "highlights": "Waikiki Beach, Diamond Head State Monument, Pearl Harbor, Hanauma Bay",
        "image_url": "https://images.unsplash.com/photo-1542259009477-d625272157b7?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "April to October",
    },
    "Zermatt": {
        "category": "Mountain",
        "description": "Car-free Swiss alpine wonderland crowned by the pyramid-shaped Matterhorn, offering world-class skiing and hiking.",
        "highlights": "Matterhorn Glacier Paradise, Gornergrat Railway, Sunnegga, Five Lakes Walk",
        "image_url": "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=1000&auto=format&fit=crop&q=85",
        "is_featured": True,
        "best_time": "December to April (Skiing), July to September (Hiking)",
    },
}

# Category fallback images for reliable display
CATEGORY_IMAGES = {
    "Beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80",
    "Coastal": "https://images.unsplash.com/photo-1533587851505-d119e13fa0d7?w=1000&auto=format&fit=crop&q=80",
    "Mountain": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1000&auto=format&fit=crop&q=80",
    "Nature": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1000&auto=format&fit=crop&q=80",
    "Cultural": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1000&auto=format&fit=crop&q=80",
    "Historical": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=1000&auto=format&fit=crop&q=80",
    "City": "https://images.unsplash.com/photo-1477959858617-67f30bc75b82?w=1000&auto=format&fit=crop&q=80",
    "Romantic": "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?w=1000&auto=format&fit=crop&q=80",
    "Adventure": "https://images.unsplash.com/photo-1526392060635-9d6019884377?w=1000&auto=format&fit=crop&q=80",
    "General": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=1000&auto=format&fit=crop&q=80",
}


def destination_image_url(name, category):
    """Return a curated city photo or a stable, varied category-matched fallback."""
    curated = CURATED_DATA.get(name)
    if curated:
        return curated["image_url"]

    legacy_fallbacks = set(CATEGORY_IMAGES.values())
    matching = [
        item["image_url"]
        for item in CURATED_DATA.values()
        if item["category"] == category and item["image_url"] not in legacy_fallbacks
    ]
    if category in {"Mountain", "Nature", "Adventure", "Coastal"}:
        matching.extend(
            item["image_url"]
            for item in CURATED_DATA.values()
            if item["category"] in {"Mountain", "Nature", "Adventure", "Coastal", "Beach"}
            and item["image_url"] not in legacy_fallbacks
            and item["image_url"] not in matching
        )
    if not matching:
        matching = [item["image_url"] for item in CURATED_DATA.values()]
    if not matching:
        return CATEGORY_IMAGES.get(category, CATEGORY_IMAGES["General"])

    digest = hashlib.sha256(name.casefold().encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % len(matching)
    return matching[index]


def refresh_destination_images():
    """Migrate legacy category-only destination photos to varied curated images."""
    legacy_fallbacks = set(CATEGORY_IMAGES.values())
    destinations = Destination.query.filter(
        Destination.image_url.in_(legacy_fallbacks)
    ).all()
    refreshed = 0

    for destination in destinations:
        curated = CURATED_DATA.get(destination.name) or CURATED_DATA.get(destination.city)
        if curated:
            destination.category = curated["category"]
            destination.description = curated["description"]
            destination.highlights = curated["highlights"]
            destination.image_url = curated["image_url"]
            destination.is_featured = curated.get("is_featured", False)
            destination.best_time = curated.get("best_time", "April to October")
        else:
            destination.image_url = destination_image_url(destination.name, destination.category)
        refreshed += 1

    cape_town = Destination.query.filter_by(name="Cape Town").first()
    if cape_town and cape_town.image_url != CURATED_DATA["Cape Town"]["image_url"]:
        cape_town.image_url = CURATED_DATA["Cape Town"]["image_url"]
        refreshed += 1

    if refreshed:
        db.session.commit()
        print(f"Refreshed {refreshed} destination images from legacy photo assignments.")
    return refreshed


def parse_trip_costs(csv_path):
    """Parse real average daily costs per destination from user_trips_dataset.csv."""
    costs = {}
    if not os.path.exists(csv_path):
        return costs

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dest_raw = row.get("Destination", "").strip('\" \t\r\n')
            if not dest_raw:
                continue
            dur_str = row.get("Duration (days)", "1")
            acc_str = row.get("Accommodation cost", "0")
            trans_str = row.get("Transportation cost", "0")

            def extract_num(s):
                digits = re.findall(r"\d+", s.replace(",", ""))
                return float(digits[0]) if digits else 0.0

            try:
                duration = float(dur_str) if dur_str else 1.0
                if duration <= 0:
                    duration = 1.0
                total_cost = extract_num(acc_str) + extract_num(trans_str)
                daily = total_cost / duration

                # Clean key: e.g. "Paris, France" -> ("Paris", "France")
                parts = [p.strip() for p in dest_raw.split(",")]
                city_key = parts[0].strip().title()
                if city_key not in costs:
                    costs[city_key] = []
                costs[city_key].append(daily)
            except Exception:
                continue

    return {k: round(sum(v) / len(v), 1) for k, v in costs.items()}


def detect_category(name, country, state=""):
    """Infer realistic category from name, country, and region."""
    text = f"{name} {state} {country}".lower()

    beach_words = ["beach", "island", "islands", "coast", "bay", "playa", "cancun", "phuket", "bali", "cabo",
                   "tulum", "maldives", "fiji", "barbados", "bahamas", "hawaii", "miami", "ibiza", "santorini",
                   "mykonos", "crete", "rhodes", "caye", "key west", "varadero", "punta cana", "san juan"]
    for w in beach_words:
        if w in text:
            return "Beach"

    mountain_words = ["banff", "aspen", "vail", "zermatt", "alps", "matterhorn", "chamonix", "breckenridge",
                      "whistler", "innsbruck", "lake placid", "teton", "glacier", "mountain", "peak", "ski",
                      "queenstown", "ushuaia", "bariloche", "manali", "pokhara", "interlaken"]
    for w in mountain_words:
        if w in text:
            return "Mountain"

    historical_words = ["rome", "athens", "cairo", "luxor", "petra", "jerusalem", "agfa", "varanasi", "prague",
                        "florence", "cusco", "machu", "cartagena", "dubrovnik", "samarkand", "bukhara",
                        "angkor", "delphi", "ephesus", "pompei", "tikal", "pyramid"]
    for w in historical_words:
        if w in text:
            return "Historical"

    nature_words = ["national park", "canyon", "yellowstone", "yosemite", "sedona", "moab", "reykjavik",
                    "rotorua", "iguazu", "amazon", "safari", "lake", "falls", "fjord"]
    for w in nature_words:
        if w in text:
            return "Nature"

    city_words = ["york", "london", "paris", "tokyo", "singapore", "hong kong", "dubai", "chicago", "toronto",
                  "seoul", "shanghai", "beijing", "bangkok", "madrid", "barcelona", "amsterdam", "berlin",
                  "sydney", "melbourne", "los angeles", "san francisco", "vienna", "boston", "seattle"]
    for w in city_words:
        if w in text:
            return "City"

    return "Cultural"


def estimate_default_cost(country):
    """Estimate a realistic daily cost based on country economy."""
    country_lower = country.lower()
    high_tier = ["switzerland", "norway", "iceland", "united states", "australia", "united kingdom",
                 "japan", "france", "germany", "austria", "sweden", "denmark", "netherlands", "singapore"]
    mid_high_tier = ["italy", "spain", "portugal", "greece", "croatia", "canada", "new zealand", "south korea"]
    mid_tier = ["argentina", "brazil", "chile", "mexico", "poland", "czech republic", "hungary", "turkey"]

    for c in high_tier:
        if c in country_lower:
            return random.randint(140, 220)
    for c in mid_high_tier:
        if c in country_lower:
            return random.randint(95, 150)
    for c in mid_tier:
        if c in country_lower:
            return random.randint(65, 110)

    # Budget tier (Southeast Asia, South Asia, parts of Latin America & Africa)
    return random.randint(40, 75)


def seed_database(app=None):
    """Main function to populate destinations in SQLite."""
    from flask import has_app_context, current_app

    if app is None:
        if has_app_context():
            ctx = None
            active_app = current_app
        else:
            active_app = create_app()
            ctx = active_app.app_context()
    else:
        active_app = app
        ctx = active_app.app_context() if not has_app_context() else None

    if ctx:
        ctx.push()

    try:
        # Clean / verify DB connection
        # Never print DATABASE_URL: it contains database credentials on hosted deployments.
        print("Connected to configured database.")

        trips_csv = os.path.join(active_app.root_path, "data", "user_trips_dataset.csv")
        dest_txt = os.path.join(active_app.root_path, "data", "world_destinations_raw.txt")

        trip_costs = parse_trip_costs(trips_csv)
        print(f"Extracted real average costs for {len(trip_costs)} destinations from user trips dataset.")

        existing_dests = {d.name.lower(): d for d in Destination.query.all()}
        print(f"Current destination count in DB before seeding: {len(existing_dests)}")

        # Keep the curated Cape Town photo accurate for destinations already in persistent databases.
        cape_town = existing_dests.get("cape town")
        curated_cape_town_image = CURATED_DATA["Cape Town"]["image_url"]
        if cape_town and cape_town.image_url != curated_cape_town_image:
            cape_town.image_url = curated_cape_town_image
            db.session.commit()

        # Replace repeated category-only fallback photos in existing production rows.
        legacy_fallbacks = set(CATEGORY_IMAGES.values())
        refreshed_images = 0
        for destination in existing_dests.values():
            if destination.image_url not in legacy_fallbacks:
                continue
            curated = CURATED_DATA.get(destination.name) or CURATED_DATA.get(destination.city)
            if curated:
                destination.category = curated["category"]
                destination.description = curated["description"]
                destination.highlights = curated["highlights"]
                destination.image_url = curated["image_url"]
                destination.is_featured = curated.get("is_featured", False)
                destination.best_time = curated.get("best_time", "April to October")
            else:
                destination.image_url = destination_image_url(destination.name, destination.category)
            refreshed_images += 1
        if refreshed_images:
            db.session.commit()
            print(f"Refreshed {refreshed_images} destination images from repeated category fallbacks.")

        destinations_to_add = []
        seen_names = set(existing_dests.keys())

        if not os.path.exists(dest_txt):
            print("World destinations file not found at:", dest_txt)
            return

        with open(dest_txt, mode="r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        print(f"Processing {len(lines)} raw destination entries...")

        for line in lines:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if not parts:
                continue

            if len(parts) == 1:
                name = parts[0]
                city = parts[0]
                state = ""
                country = ""
            elif len(parts) == 2:
                name = parts[0]
                city = parts[0]
                state = ""
                country = parts[1]
            else:
                name = parts[0]
                city = parts[0]
                state = parts[1]
                country = parts[2]

            name_key = name.lower()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            # Match with curated data or generate realistic attributes
            curated = CURATED_DATA.get(name) or CURATED_DATA.get(city)

            if curated:
                category = curated["category"]
                description = curated["description"]
                highlights = curated["highlights"]
                image_url = curated["image_url"]
                is_featured = curated.get("is_featured", False)
                best_time = curated.get("best_time", "April to October")
            else:
                category = detect_category(name, country, state)
                location_str = f"{city}, {country}" if country else city
                description = f"Experience the captivating sights, vibrant local hospitality, and scenic landscapes of {location_str}."
                highlights = f"{city} Historic Center, Scenic Viewpoints, Local Markets, Cultural Landmarks"
                image_url = destination_image_url(name, category)
                is_featured = False
                best_time = "April to October"

            # Determine cost
            if name in trip_costs:
                avg_cost = trip_costs[name]
            elif city in trip_costs:
                avg_cost = trip_costs[city]
            else:
                avg_cost = estimate_default_cost(country)

            rating = round(random.uniform(4.5, 4.9), 1)
            review_count = random.randint(45, 380)

            dest = Destination(
                name=name,
                city=city,
                state=state,
                country=country,
                category=category,
                description=description,
                rating=rating,
                review_count=review_count,
                best_time=best_time,
                avg_cost_per_day=avg_cost,
                currency="USD",
                image_url=image_url,
                highlights=highlights,
                is_featured=is_featured,
            )
            destinations_to_add.append(dest)

        if destinations_to_add:
            print(f"Adding {len(destinations_to_add)} new destinations to the database...")
            # Batch insert for high performance
            batch_size = 100
            for i in range(0, len(destinations_to_add), batch_size):
                db.session.add_all(destinations_to_add[i:i + batch_size])
                db.session.commit()

        total_dests = Destination.query.count()
        print(f"🎉 Successfully seeded! Total destinations now in database: {total_dests}")
    finally:
        if ctx:
            ctx.pop()


if __name__ == "__main__":
    seed_database()
