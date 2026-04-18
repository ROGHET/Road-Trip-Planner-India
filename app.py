from functools import lru_cache
import heapq
import math
from pathlib import Path
import time

import requests
from flask import Flask, jsonify, request, send_file

try:
    from flask_cors import CORS
except ImportError:
    CORS = None


app = Flask(__name__)
if CORS is not None:
    CORS(app)


BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "templates" / "index.html"
AVERAGE_SPEED_KMPH = 60
CO2_KG_PER_KM = 0.12
DEFAULT_HIGHWAY_TOLL_RATE = 0.9
SUPPORTED_ALGORITHMS = {"dijkstra", "floyd_warshall"}


NODES = {
    "Delhi": (28.7041, 77.1025),
    "Noida": (28.5721, 77.3560),
    "Gurgaon": (28.4595, 77.0266),
    "Chandigarh": (30.7333, 76.7597),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Agra": (27.1767, 78.0081),
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Ahmedabad": (23.0225, 72.5714),
    "Surat": (21.1702, 72.8311),
    "Rajkot": (22.3039, 70.8022),
    "Vadodara": (22.3072, 73.1812),
    "Hyderabad": (17.3850, 78.4867),
    "Bangalore": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kochi": (9.9312, 76.2673),
    "Coimbatore": (11.0066, 76.9655),
    "Madurai": (9.9189, 78.1193),
    "Visakhapatnam": (17.6869, 83.2185),
    "Kolkata": (22.5726, 88.3639),
    "Patna": (25.5941, 85.1376),
    "Guwahati": (26.1445, 91.7362),
    "Ranchi": (23.3441, 85.3096),
    "Bhubaneswar": (20.2961, 85.8245),
    "Shimla": (31.1048, 77.1734),
    "Manali": (32.2432, 77.1892),
    "Nainital": (29.3803, 79.4636),
    "Gibhi": (31.6369, 77.3486),
    "Shojha": (31.6033, 77.3764),
    "Dharamshala": (32.2190, 76.3234),
    "Mussoorie": (30.4598, 78.0644),
    "Rishikesh": (30.0869, 78.2676),
    "Dehradun": (30.3165, 78.0322),
    "Indore": (22.7196, 75.8577),
    "Bhopal": (23.2599, 77.4126),
    "Amritsar": (31.6340, 74.8723),
    "Ooty": (11.4102, 76.6950),
    "Munnar": (10.0889, 77.0595),
    "Mahabaleshwar": (17.9235, 73.6586),
    "Jabalpur": (23.1670, 79.9322),
    "Varanasi": (25.3176, 82.9739),
    "Gwalior": (26.2183, 78.1828),
    "Raipur": (21.2514, 81.6296),
    "Jamshedpur": (22.8046, 86.2029),
}


CONNECTIONS = [
    ("Delhi", "Noida", 25),
    ("Delhi", "Gurgaon", 35),
    ("Noida", "Gurgaon", 50),
    ("Delhi", "Chandigarh", 240),
    ("Delhi", "Jaipur", 260),
    ("Delhi", "Agra", 206),
    ("Jaipur", "Agra", 240),
    ("Jaipur", "Ahmedabad", 660),
    ("Chandigarh", "Delhi", 240),
    ("Delhi", "Lucknow", 450),
    ("Lucknow", "Kanpur", 80),
    ("Kanpur", "Lucknow", 80),
    ("Delhi", "Patna", 640),
    ("Lucknow", "Patna", 350),
    ("Delhi", "Agra", 206),
    ("Agra", "Jaipur", 240),
    ("Mumbai", "Pune", 150),
    ("Pune", "Nagpur", 720),
    ("Mumbai", "Nagpur", 900),
    ("Mumbai", "Ahmedabad", 580),
    ("Ahmedabad", "Rajkot", 250),
    ("Rajkot", "Surat", 320),
    ("Ahmedabad", "Vadodara", 120),
    ("Surat", "Mumbai", 270),
    ("Hyderabad", "Bangalore", 570),
    ("Bangalore", "Chennai", 350),
    ("Chennai", "Madurai", 150),
    ("Hyderabad", "Visakhapatnam", 550),
    ("Bangalore", "Coimbatore", 240),
    ("Kochi", "Coimbatore", 210),
    ("Madurai", "Kochi", 220),
    ("Kolkata", "Patna", 540),
    ("Patna", "Guwahati", 850),
    ("Guwahati", "Kolkata", 1200),
    ("Kolkata", "Bhubaneswar", 480),
    ("Ranchi", "Patna", 280),
    ("Nagpur", "Hyderabad", 560),
    ("Nagpur", "Kolkata", 900),
    ("Nagpur", "Bangalore", 850),
    ("Jaipur", "Agra", 240),
    ("Agra", "Lucknow", 380),
    ("Hyderabad", "Bangalore", 570),
    ("Bangalore", "Chennai", 350),
    ("Pune", "Hyderabad", 650),
    ("Pune", "Bangalore", 650),
    ("Delhi", "Dehradun", 240),
    ("Dehradun", "Mussoorie", 35),
    ("Dehradun", "Rishikesh", 45),
    ("Delhi", "Shimla", 340),
    ("Shimla", "Manali", 250),
    ("Shimla", "Gibhi", 150),
    ("Gibhi", "Shojha", 15),
    ("Delhi", "Nainital", 310),
    ("Chandigarh", "Shimla", 115),
    ("Amritsar", "Chandigarh", 230),
    ("Mumbai", "Mahabaleshwar", 260),
    ("Mahabaleshwar", "Pune", 120),
    ("Bangalore", "Ooty", 270),
    ("Kochi", "Munnar", 130),
    ("Jaipur", "Indore", 450),
    ("Indore", "Bhopal", 195),
    ("Bhopal", "Nagpur", 350),
    ("Agra", "Bhopal", 440),
    ("Manali", "Dharamshala", 230),
    ("Ooty", "Coimbatore", 85),
    ("Munnar", "Madurai", 155),
    ("Patna", "Varanasi", 250),
    ("Varanasi", "Lucknow", 320),
    ("Agra", "Gwalior", 120),
    ("Gwalior", "Bhopal", 420),
    ("Bhopal", "Jabalpur", 330),
    ("Jabalpur", "Nagpur", 270),
    ("Nagpur", "Raipur", 285),
    ("Raipur", "Visakhapatnam", 580),
    ("Ranchi", "Jamshedpur", 130),
    ("Jamshedpur", "Kolkata", 280),
    ("Indore", "Nagpur", 440),
    ("Indore", "Ahmedabad", 390),
]


def edge_key(city_a, city_b):
    return tuple(sorted((city_a, city_b)))


EDGE_METADATA = {
    edge_key("Delhi", "Noida"): {"highway": "Noida Link Road", "road_name": "Noida Link Road", "flat_toll": 0},
    edge_key("Delhi", "Gurgaon"): {"highway": "NH 48", "road_name": "Delhi-Gurgaon Expressway", "flat_toll": 0},
    edge_key("Gurgaon", "Noida"): {"highway": "DND Flyway and NH 48", "road_name": "DND Flyway Corridor", "flat_toll": 0},
    edge_key("Delhi", "Chandigarh"): {"highway": "NH 44", "road_name": "Delhi-Chandigarh Highway", "toll_rate": 0.95},
    edge_key("Delhi", "Jaipur"): {"highway": "NH 48", "road_name": "Delhi-Jaipur Highway", "toll_rate": 0.95},
    edge_key("Delhi", "Agra"): {"highway": "Yamuna Expressway", "road_name": "Yamuna Expressway", "toll_rate": 1.75},
    edge_key("Jaipur", "Agra"): {"highway": "NH 21", "road_name": "Jaipur-Agra Corridor", "toll_rate": 0.65},
    edge_key("Jaipur", "Ahmedabad"): {"highway": "NH 48", "road_name": "Jaipur-Ahmedabad Highway", "toll_rate": 0.9},
    edge_key("Delhi", "Lucknow"): {"highway": "Agra-Lucknow Expressway", "road_name": "Delhi-Lucknow Corridor", "toll_rate": 1.2},
    edge_key("Lucknow", "Kanpur"): {"highway": "NH 27", "road_name": "Lucknow-Kanpur Highway", "toll_rate": 0.7},
    edge_key("Delhi", "Patna"): {"highway": "NH 19", "road_name": "Grand Trunk Corridor", "toll_rate": 0.95},
    edge_key("Lucknow", "Patna"): {"highway": "NH 27", "road_name": "Lucknow-Patna Corridor", "toll_rate": 0.85},
    edge_key("Mumbai", "Pune"): {"highway": "Mumbai-Pune Expressway", "road_name": "Mumbai-Pune Expressway", "flat_toll": 320},
    edge_key("Pune", "Nagpur"): {"highway": "Samruddhi Mahamarg Corridor", "road_name": "Pune-Nagpur Corridor", "toll_rate": 1.1},
    edge_key("Mumbai", "Nagpur"): {"highway": "Samruddhi Mahamarg", "road_name": "Mumbai-Nagpur Corridor", "toll_rate": 1.25},
    edge_key("Mumbai", "Ahmedabad"): {"highway": "NH 48", "road_name": "Mumbai-Ahmedabad Highway", "toll_rate": 0.95},
    edge_key("Ahmedabad", "Rajkot"): {"highway": "NH 47", "road_name": "Ahmedabad-Rajkot Highway", "toll_rate": 0.85},
    edge_key("Rajkot", "Surat"): {"highway": "NH 48 Corridor", "road_name": "Rajkot-Surat Corridor", "toll_rate": 0.8},
    edge_key("Ahmedabad", "Vadodara"): {"highway": "NE 1", "road_name": "Ahmedabad-Vadodara Expressway", "toll_rate": 1.2},
    edge_key("Surat", "Mumbai"): {"highway": "NH 48", "road_name": "Surat-Mumbai Highway", "toll_rate": 1.0},
    edge_key("Hyderabad", "Bangalore"): {"highway": "NH 44", "road_name": "Hyderabad-Bangalore Highway", "toll_rate": 0.95},
    edge_key("Bangalore", "Chennai"): {"highway": "NH 48", "road_name": "Bangalore-Chennai Express Corridor", "toll_rate": 0.95},
    edge_key("Chennai", "Madurai"): {"highway": "NH 38", "road_name": "Chennai-Madurai Corridor", "toll_rate": 0.8},
    edge_key("Hyderabad", "Visakhapatnam"): {"highway": "NH 65 and NH 16", "road_name": "Hyderabad-Visakhapatnam Corridor", "toll_rate": 0.8},
    edge_key("Bangalore", "Coimbatore"): {"highway": "NH 544", "road_name": "Bangalore-Coimbatore Highway", "toll_rate": 0.9},
    edge_key("Kochi", "Coimbatore"): {"highway": "NH 544", "road_name": "Kochi-Coimbatore Highway", "toll_rate": 0.8},
    edge_key("Madurai", "Kochi"): {"highway": "NH 85", "road_name": "Madurai-Kochi Highway", "toll_rate": 0.55},
    edge_key("Kolkata", "Patna"): {"highway": "NH 19", "road_name": "Kolkata-Patna Highway", "toll_rate": 0.9},
    edge_key("Patna", "Guwahati"): {"highway": "NH 27", "road_name": "Patna-Guwahati Corridor", "toll_rate": 0.8},
    edge_key("Guwahati", "Kolkata"): {"highway": "NH 27", "road_name": "Guwahati-Kolkata Corridor", "toll_rate": 0.8},
    edge_key("Kolkata", "Bhubaneswar"): {"highway": "NH 16", "road_name": "Kolkata-Bhubaneswar Highway", "toll_rate": 0.9},
    edge_key("Ranchi", "Patna"): {"highway": "NH 20", "road_name": "Ranchi-Patna Highway", "toll_rate": 0.75},
    edge_key("Nagpur", "Hyderabad"): {"highway": "NH 44", "road_name": "Nagpur-Hyderabad Highway", "toll_rate": 0.9},
    edge_key("Nagpur", "Kolkata"): {"highway": "NH 53", "road_name": "Nagpur-Kolkata Corridor", "toll_rate": 0.85},
    edge_key("Nagpur", "Bangalore"): {"highway": "NH 44", "road_name": "Nagpur-Bangalore Corridor", "toll_rate": 0.85},
    edge_key("Agra", "Lucknow"): {"highway": "Agra-Lucknow Expressway", "road_name": "Agra-Lucknow Expressway", "toll_rate": 1.2},
    edge_key("Pune", "Hyderabad"): {"highway": "NH 65", "road_name": "Pune-Hyderabad Highway", "toll_rate": 0.85},
    edge_key("Pune", "Bangalore"): {"highway": "NH 48", "road_name": "Pune-Bangalore Highway", "toll_rate": 0.95},
    edge_key("Delhi", "Dehradun"): {"highway": "NH 724", "road_name": "Delhi-Dehradun Expressway", "toll_rate": 0.85},
    edge_key("Dehradun", "Mussoorie"): {"highway": "Mussoorie Rd", "road_name": "Dehradun-Mussoorie Hill Road", "flat_toll": 0},
    edge_key("Dehradun", "Rishikesh"): {"highway": "NH 7", "road_name": "Dehradun-Rishikesh Highway", "flat_toll": 0},
    edge_key("Delhi", "Shimla"): {"highway": "NH 44 and NH 5", "road_name": "Delhi-Shimla Corridor", "toll_rate": 0.95},
    edge_key("Shimla", "Manali"): {"highway": "NH 21", "road_name": "Shimla-Manali Highway", "flat_toll": 0},
    edge_key("Shimla", "Gibhi"): {"highway": "NH 5", "road_name": "Shimla-Gibhi Jalori Pass Route", "flat_toll": 0},
    edge_key("Gibhi", "Shojha"): {"highway": "Jalori Pass Rd", "road_name": "Gibhi-Shojha link", "flat_toll": 0},
    edge_key("Delhi", "Nainital"): {"highway": "NH 9", "road_name": "Delhi-Nainital Highway", "toll_rate": 0.75},
    edge_key("Chandigarh", "Shimla"): {"highway": "NH 5", "road_name": "Chandigarh-Shimla Expressway", "toll_rate": 1.1},
    edge_key("Amritsar", "Chandigarh"): {"highway": "NH 344A", "road_name": "Amritsar-Chandigarh Highway", "toll_rate": 0.85},
    edge_key("Mumbai", "Mahabaleshwar"): {"highway": "NH 4", "road_name": "Mumbai-Mahabaleshwar Road", "toll_rate": 0.9},
    edge_key("Mahabaleshwar", "Pune"): {"highway": "NH 4", "road_name": "Mahabaleshwar-Pune Road", "flat_toll": 0},
    edge_key("Bangalore", "Ooty"): {"highway": "NH 275", "road_name": "Bangalore-Ooty Highway", "toll_rate": 0.8},
    edge_key("Kochi", "Munnar"): {"highway": "NH 85", "road_name": "Kochi-Munnar Road", "flat_toll": 0},
    edge_key("Jaipur", "Indore"): {"highway": "NH 52", "road_name": "Jaipur-Indore Highway", "toll_rate": 0.85},
    edge_key("Indore", "Bhopal"): {"highway": "NH 47", "road_name": "Indore-Bhopal Highway", "toll_rate": 0.9},
    edge_key("Bhopal", "Nagpur"): {"highway": "NH 46", "road_name": "Bhopal-Nagpur Highway", "toll_rate": 0.85},
    edge_key("Agra", "Bhopal"): {"highway": "NH 44", "road_name": "Agra-Bhopal Corridor", "toll_rate": 0.9},
    edge_key("Manali", "Dharamshala"): {"highway": "NH 154", "road_name": "Manali-Dharamshala Scenic Route", "flat_toll": 0},
    edge_key("Ooty", "Coimbatore"): {"highway": "NH 181", "road_name": "Ooty-Coimbatore Ghat Road", "flat_toll": 0},
    edge_key("Munnar", "Madurai"): {"highway": "NH 85", "road_name": "Munnar-Madurai Highway", "flat_toll": 0},
    edge_key("Patna", "Varanasi"): {"highway": "NH 19", "road_name": "Patna-Varanasi Highway", "toll_rate": 1.4},
    edge_key("Varanasi", "Lucknow"): {"highway": "NH 31", "road_name": "Varanasi-Lucknow Highway", "toll_rate": 1.4},
    edge_key("Agra", "Gwalior"): {"highway": "NH 44", "road_name": "Agra-Gwalior Road", "toll_rate": 1.4},
    edge_key("Gwalior", "Bhopal"): {"highway": "NH 44", "road_name": "Gwalior-Bhopal Corridor", "toll_rate": 1.4},
    edge_key("Bhopal", "Jabalpur"): {"highway": "NH 45", "road_name": "Bhopal-Jabalpur Highway", "toll_rate": 1.4},
    edge_key("Jabalpur", "Nagpur"): {"highway": "NH 44", "road_name": "Jabalpur-Nagpur Corridor", "toll_rate": 1.4},
    edge_key("Nagpur", "Raipur"): {"highway": "NH 53", "road_name": "Nagpur-Raipur Highway", "toll_rate": 1.4},
    edge_key("Raipur", "Visakhapatnam"): {"highway": "NH 26", "road_name": "Raipur-Visakhapatnam Corridor", "toll_rate": 1.4},
    edge_key("Ranchi", "Jamshedpur"): {"highway": "NH 43", "road_name": "Ranchi-Jamshedpur Highway", "toll_rate": 1.4},
    edge_key("Jamshedpur", "Kolkata"): {"highway": "NH 16", "road_name": "Jamshedpur-Kolkata Highway", "toll_rate": 1.4},
    edge_key("Indore", "Nagpur"): {"highway": "NH 47", "road_name": "Indore-Nagpur Highway", "toll_rate": 1.4},
    edge_key("Indore", "Ahmedabad"): {"highway": "NH 47", "road_name": "Indore-Ahmedabad Highway", "toll_rate": 1.4},
}

# Update existing tolls to 2026 researched rates
EDGE_METADATA[edge_key("Delhi", "Agra")]["toll_rate"] = 2.95
EDGE_METADATA[edge_key("Agra", "Lucknow")]["toll_rate"] = 2.95
EDGE_METADATA[edge_key("Pune", "Nagpur")]["toll_rate"] = 2.45
EDGE_METADATA[edge_key("Mumbai", "Nagpur")]["toll_rate"] = 2.45
EDGE_METADATA[edge_key("Mumbai", "Pune")]["flat_toll"] = 320


def haversine_distance(coord1, coord2):
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(6371 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))), 2)


def build_graph():
    graph = {node: {} for node in NODES}

    for u, v, dist in CONNECTIONS:
        graph[u][v] = {"dist": dist}
        graph[v][u] = {"dist": dist}

    return graph


GRAPH = build_graph()
UNIQUE_EDGE_COUNT = len({tuple(sorted((u, v))) for u, v, _ in CONNECTIONS})


def dijkstra(graph, start, end):
    if start not in graph or end not in graph:
        return float("inf"), []

    queue = [(0, start, [])]
    seen = set()
    mins = {start: 0}

    while queue:
        cost, node, path = heapq.heappop(queue)
        if node in seen:
            continue

        seen.add(node)
        path = path + [node]

        if node == end:
            return cost, path

        for next_node, attrs in graph.get(node, {}).items():
            if next_node in seen:
                continue

            next_cost = cost + attrs["dist"]
            if next_cost < mins.get(next_node, float("inf")):
                mins[next_node] = next_cost
                heapq.heappush(queue, (next_cost, next_node, path))

    return float("inf"), []


def floyd_warshall(graph):
    nodes = list(graph.keys())
    dist = {}
    next_node = {}

    for u in nodes:
        dist[u] = {}
        next_node[u] = {}
        for v in nodes:
            if u == v:
                dist[u][v] = 0
                next_node[u][v] = v
            elif v in graph[u]:
                dist[u][v] = graph[u][v]["dist"]
                next_node[u][v] = v
            else:
                dist[u][v] = float("inf")
                next_node[u][v] = None

    for k in nodes:
        for i in nodes:
            for j in nodes:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
                    next_node[i][j] = next_node[i][k]

    return dist, next_node


@lru_cache(maxsize=1)
def get_floyd_cache():
    return floyd_warshall(GRAPH)


def reconstruct_path_fw(next_node, start, end):
    if start == end:
        return [start]

    if next_node[start][end] is None:
        return []

    path = [start]
    current = start

    while current != end:
        current = next_node[current][end]
        path.append(current)

    return path


def get_edge_profile(city_a, city_b):
    distance = GRAPH[city_a][city_b]["dist"]
    metadata = EDGE_METADATA.get(edge_key(city_a, city_b), {})

    if "flat_toll" in metadata:
        estimated_toll = float(metadata["flat_toll"])
        toll_rate = None
    else:
        toll_rate = metadata.get("toll_rate", DEFAULT_HIGHWAY_TOLL_RATE)
        estimated_toll = round(distance * toll_rate, 2)

    return {
        "highway": metadata.get("highway", "Regional highway connector"),
        "road_name": metadata.get("road_name", metadata.get("highway", "Regional road")),
        "distance": round(distance, 2),
        "estimated_toll": round(estimated_toll, 2),
        "toll_basis": "flat" if "flat_toll" in metadata else "rate",
        "toll_rate_per_km": toll_rate,
    }


def format_osrm_instruction(step):
    maneuver = step.get("maneuver", {})
    maneuver_type = (maneuver.get("type") or "continue").replace("_", " ")
    modifier = maneuver.get("modifier")
    name = step.get("name") or ""
    ref = step.get("ref") or ""
    destinations = step.get("destinations") or ""

    road_label = ref or name or "the current road"

    if maneuver_type == "depart":
        instruction = f"Depart and follow {road_label}"
    elif maneuver_type == "arrive":
        instruction = "Arrive at your destination"
    elif maneuver_type == "roundabout":
        instruction = f"Enter the roundabout and continue toward {road_label}"
    elif maneuver_type == "merge":
        instruction = f"Merge onto {road_label}"
    elif maneuver_type == "fork":
        direction = f" {modifier}" if modifier else ""
        instruction = f"Keep{direction} to stay on {road_label}"
    elif modifier:
        instruction = f"Turn {modifier} onto {road_label}"
    else:
        instruction = f"Continue on {road_label}"

    if destinations and maneuver_type != "arrive":
        instruction = f"{instruction} toward {destinations}"

    return instruction


def build_fallback_directions(path_nodes):
    directions = []

    for index, (from_city, to_city) in enumerate(zip(path_nodes, path_nodes[1:]), start=1):
        step = get_edge_profile(from_city, to_city)
        time_minutes = round((step["distance"] / AVERAGE_SPEED_KMPH) * 60, 1)
        directions.append({
            "index": index,
            "leg": f"{from_city} to {to_city}",
            "instruction": f"Drive from {from_city} to {to_city} via {step['highway']}",
            "road": step["road_name"],
            "highway": step["highway"],
            "distance_km": step["distance"],
            "time_minutes": time_minutes,
        })

    return directions


OSRM_CACHE = {}

def get_live_route_bundle(path_nodes):
    if len(path_nodes) < 2:
        return {
            "geometry": [list(NODES[node]) for node in path_nodes],
            "distance_km": 0,
            "time_minutes": 0,
            "leg_summaries": [],
            "directions": [],
            "source": "Static city coordinates",
        }

    cache_key = tuple(path_nodes)
    if cache_key in OSRM_CACHE:
        return OSRM_CACHE[cache_key]

    try:
        coords = ";".join(f"{NODES[node][1]},{NODES[node][0]}" for node in path_nodes)
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{coords}?overview=full&geometries=geojson&steps=true"
        )
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok":
            raise ValueError("OSRM returned a non-OK response")

        route = payload["routes"][0]
        geometry = [[lat, lon] for lon, lat in route["geometry"]["coordinates"]]
        directions = []
        leg_summaries = []

        for leg_index, leg in enumerate(route.get("legs", [])):
            start_city = path_nodes[leg_index]
            end_city = path_nodes[leg_index + 1]
            edge_profile = get_edge_profile(start_city, end_city)
            leg_summaries.append({
                "from": start_city,
                "to": end_city,
                "distance": round(leg.get("distance", 0) / 1000, 2),
                "time_minutes": round(leg.get("duration", 0) / 60, 1),
                "highway": edge_profile["highway"],
                "road_name": edge_profile["road_name"],
            })

            for step in leg.get("steps", []):
                distance_km = round(step.get("distance", 0) / 1000, 2)
                time_minutes = round(step.get("duration", 0) / 60, 1)

                # Skip tiny alignment instructions that add noise in printouts.
                if distance_km < 0.08 and step.get("maneuver", {}).get("type") not in {"depart", "arrive"}:
                    continue

                directions.append({
                    "index": len(directions) + 1,
                    "leg": f"{start_city} to {end_city}",
                    "instruction": format_osrm_instruction(step),
                    "road": step.get("name") or step.get("ref") or "Unnamed road",
                    "highway": step.get("ref") or step.get("name") or "Road segment",
                    "distance_km": distance_km,
                    "time_minutes": time_minutes,
                })

        bundle = {
            "geometry": geometry,
            "distance_km": round(route.get("distance", 0) / 1000, 2),
            "time_minutes": round(route.get("duration", 0) / 60, 1),
            "leg_summaries": leg_summaries,
            "directions": directions,
            "source": "Live OpenStreetMap road guidance via OSRM",
        }
        OSRM_CACHE[cache_key] = bundle
        return bundle
    except Exception:
        return {
            "geometry": [list(NODES[node]) for node in path_nodes],
            "distance_km": 0,
            "time_minutes": 0,
            "leg_summaries": [],
            "directions": build_fallback_directions(path_nodes),
            "source": "Configured corridor guidance fallback",
        }


def validate_waypoints(waypoints):
    return [city for city in waypoints if city not in NODES]


def compute_route(waypoints, algorithm):
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    total_dist = 0.0
    full_path = []
    algorithm_trace = []

    if algorithm == "floyd_warshall":
        dist_matrix, next_node = get_floyd_cache()

    for segment_src, segment_dst in zip(waypoints, waypoints[1:]):
        if algorithm == "dijkstra":
            dist, path = dijkstra(GRAPH, segment_src, segment_dst)
        else:
            dist = dist_matrix[segment_src][segment_dst]
            path = reconstruct_path_fw(next_node, segment_src, segment_dst)

        if math.isinf(dist) or not path:
            raise ValueError(f"No route: {segment_src} -> {segment_dst}")

        total_dist += dist
        if not full_path:
            full_path.extend(path)
        else:
            full_path.extend(path[1:])

        algorithm_trace.append({
            "segment": f"{segment_src} -> {segment_dst}",
            "distance": round(dist, 2),
            "path": path,
        })

    return {
        "distance": round(total_dist, 2),
        "path": full_path,
        "algorithm_trace": algorithm_trace,
    }


def build_steps(path_nodes):
    steps = []

    for from_city, to_city in zip(path_nodes, path_nodes[1:]):
        edge_profile = get_edge_profile(from_city, to_city)
        distance = edge_profile["distance"]
        time_minutes = round((distance / AVERAGE_SPEED_KMPH) * 60, 1)
        steps.append({
            "from": from_city,
            "to": to_city,
            "distance": distance,
            "time_minutes": time_minutes,
            "time_hours": round(time_minutes / 60, 2),
            "highway": edge_profile["highway"],
            "road_name": edge_profile["road_name"],
            "estimated_toll": edge_profile["estimated_toll"],
            "toll_basis": edge_profile["toll_basis"],
            "toll_rate_per_km": edge_profile["toll_rate_per_km"],
        })

    return steps


def generate_city_tips(city_name):
    tips = {
        "Delhi": "Use the Eastern Peripheral Expressway to bypass inner-city congestion and reduce idle emissions.",
        "Mumbai": "Plan travel during non-peak hours to avoid heavy stop-and-go traffic on the Western Express Highway.",
        "Bangalore": "Optimize route via NICE road to maintain steady speeds and improve fuel efficiency.",
        "Chennai": "Leverage the Outer Ring Road for smoother transit and lower fuel consumption.",
        "Nagpur": "Check tyre pressure before entering the Samruddhi Mahamarg for optimal high-speed performance.",
        "Indore": "Maintain steady speeds on the bypass road to minimize fuel waste in local traffic.",
        "Jaipur": "Use the 200 Feet Bypass to avoid city centers and reduce trip duration.",
        "Pune": "Avoid travel during heavy rain or peak hour congestions on the Katraj-Dehu Road bypass.",
        "Ahmedabad": "Use the Sardar Patel Ring Road to maintain a consistent cruising speed.",
        "Shimla": "Avoid aggressive acceleration on steep climbs to keep engine emissions in check.",
        "Gwalior": "Ensure vehicle cooling systems are efficient for hot-weather corridor transit.",
        "Jamshedpur": "Use the industrial bypass roads to avoid heavy-vehicle congestion.",
    }
    return tips.get(city_name, f"Maintain a steady speed in {city_name} to optimize fuel consumption and reduce emissions.")


def generate_eco_tips(total_distance, total_time_minutes):
    tips = [
        "Keep tyre pressure at the manufacturer-recommended level and avoid carrying unnecessary luggage.",
        "Drive smoothly with fewer hard accelerations and maintain a steady cruising speed where it is safe.",
        "Use digital toll payment and plan breaks ahead of time to reduce idling at fuel or food stops.",
    ]

    if total_distance >= 350:
        tips.append("If possible, split the driving load with another traveler or combine this trip with other errands.")

    if total_time_minutes >= 360:
        tips.append("Plan rest stops before peak congestion windows so you spend less time crawling in traffic.")

    return tips


def calculate_network_metrics():
    dist_matrix, _ = get_floyd_cache()
    metrics = {
        "total_nodes": len(NODES),
        "total_edges": UNIQUE_EDGE_COUNT,
        "avg_distance": 0,
        "connectivity": 0,
        "network_reach": 0,
        "unreachable_pairs": 0,
    }

    distances = []
    reachable = 0
    max_distance = 0
    nodes_list = list(NODES.keys())

    for index, source in enumerate(nodes_list):
        for destination in nodes_list[index + 1:]:
            distance = dist_matrix[source][destination]
            if math.isinf(distance):
                metrics["unreachable_pairs"] += 1
                continue

            distances.append(distance)
            reachable += 1
            max_distance = max(max_distance, distance)

    if distances:
        metrics["avg_distance"] = round(sum(distances) / len(distances), 2)

    total_pairs = len(nodes_list) * (len(nodes_list) - 1) / 2
    metrics["connectivity"] = round((reachable / total_pairs) * 100, 2) if total_pairs else 0
    metrics["network_reach"] = round(max_distance, 2)
    return metrics


@app.route("/city-status/<city_name>")
def get_city_status(city_name):
    if city_name not in NODES:
        return jsonify({"error": "City not found"}), 404

    import random
    import datetime
    import math

    # Calculate current hour in IST
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    hour_float = now_ist.hour + now_ist.minute / 60.0
    
    # Regional Profiles
    HILL_CITIES = {"Shimla", "Manali", "Nainital", "Gibhi", "Shojha", "Dharamshala", "Mussoorie", "Ooty", "Munnar", "Mahabaleshwar"}
    COASTAL_CITIES = {"Mumbai", "Chennai", "Kochi", "Visakhapatnam"}
    
    # Regional Temp Config (Idealized April Patterns)
    # Sinusoidal curve: Temp = Base + Range * sin((hour-8) * pi / 12)
    # Peaks around 4 PM (hour 16), Low around 4 AM (hour 4)
    if city_name in HILL_CITIES:
        base, t_range = 14, 8  # Range 14 to 22
    elif city_name in COASTAL_CITIES:
        base, t_range = 28, 5  # Range 28 to 33 (Humid, less swing)
    else:
        base, t_range = 30, 10  # Range 30 to 40 (Plains/Central)

    temp_val = base + t_range * math.sin((hour_float - 10) * math.pi / 12)
    current_temp = round(temp_val + random.uniform(-1, 1), 1)

    # Dynamic AQI simulation
    # Anchors for Delhi/Mumbai, with a small hourly drift
    if city_name == "Delhi":
        base_aqi = 177
    elif city_name == "Mumbai":
        base_aqi = 119
    else:
        base_aqi = random.randint(40, 80) if city_name in HILL_CITIES else random.randint(100, 240)
    
    # Drift AQI slightly based on hour (worse in morning/night inversions)
    aqi_drift = 20 * math.cos(hour_float * math.pi / 12)
    current_aqi = int(base_aqi + aqi_drift + random.randint(-5, 5))

    is_night = now_ist.hour >= 19 or now_ist.hour < 6

    if is_night:
        night_conditions = ["Clear Night", "Partly Cloudy Night", "Mist", "Hazy Night"]
        condition = random.choice(night_conditions)
        traffic = random.choice(["Light", "Light", "Moderate"])
    else:
        day_conditions = ["Sunny", "Clear Sky", "Partly Cloudy", "Haze"]
        condition = random.choice(day_conditions)
        traffic = random.choice(["Moderate", "Heavy", "Heavy", "Congested"])

    return jsonify({
        "city": city_name,
        "aqi": current_aqi,
        "aqi_label": "Good" if current_aqi <= 50 else "Moderate" if current_aqi <= 100 else "Poor" if current_aqi <= 200 else "Very Poor",
        "temperature": f"{current_temp}°C",
        "condition": condition,
        "traffic_status": traffic,
        "last_updated": now_ist.strftime("%H:%M:%S")
    })


def serialize_route(src, dst, stops, algorithm, route_result):
    network_distance = route_result["distance"]
    path_nodes = route_result["path"]
    segment_steps = build_steps(path_nodes)
    live_route = get_live_route_bundle(path_nodes)
    live_leg_summaries = live_route.get("leg_summaries", [])

    if len(live_leg_summaries) == len(segment_steps):
        merged_steps = []
        for base_step, live_step in zip(segment_steps, live_leg_summaries):
            merged_step = {**base_step}
            merged_step["distance"] = live_step["distance"]
            merged_step["time_minutes"] = live_step["time_minutes"]
            merged_step["time_hours"] = round(live_step["time_minutes"] / 60, 2)
            merged_step["city_tip"] = generate_city_tips(merged_step["from"])
            if merged_step["toll_basis"] == "rate" and merged_step["toll_rate_per_km"] is not None:
                merged_step["estimated_toll"] = round(
                    merged_step["distance"] * merged_step["toll_rate_per_km"], 2
                )
            merged_steps.append(merged_step)
        segment_steps = merged_steps

    total_distance = live_route.get("distance_km") or network_distance
    total_time_minutes = live_route["time_minutes"] or round((total_distance / AVERAGE_SPEED_KMPH) * 60, 1)
    total_toll_cost = round(sum(step["estimated_toll"] for step in segment_steps), 2)
    eco_tips = generate_eco_tips(total_distance, total_time_minutes)

    return {
        "src": src,
        "dst": dst,
        "stops": stops,
        "algorithm": algorithm,
        "distance": total_distance,
        "network_distance": network_distance,
        "time": total_time_minutes,
        "time_minutes": total_time_minutes,
        "time_hours": round(total_time_minutes / 60, 2),
        "path": path_nodes,
        "geometry": live_route["geometry"],
        "steps": segment_steps,
        "directions": live_route["directions"],
        "algorithm_trace": route_result["algorithm_trace"],
        "co2_emissions": round(total_distance * CO2_KG_PER_KM, 2),
        "estimated_toll_cost": total_toll_cost,
        "toll_note": "Toll values are estimates based on corridor profiles and can differ from live plaza rates.",
        "road_guidance_source": live_route["source"],
        "eco_tips": eco_tips,
    }


def parse_route_request():
    data = request.get_json(silent=True) or {}
    src = data.get("src")
    dst = data.get("dst")
    stops = [stop for stop in data.get("stops", []) if stop and stop != "None"]
    algorithm = data.get("algorithm", "dijkstra")
    return src, dst, stops, algorithm


@app.route("/")
def index():
    return send_file(INDEX_FILE)


@app.route("/nodes")
def get_nodes():
    return jsonify(NODES)


@app.route("/connections")
def get_connections():
    return jsonify(CONNECTIONS)


@app.route("/calculate", methods=["POST"])
def calculate():
    src, dst, stops, algorithm = parse_route_request()

    if not src or not dst:
        return jsonify({"error": "Source and destination are required."}), 400

    waypoints = [src] + stops + [dst]
    invalid_cities = validate_waypoints(waypoints)
    if invalid_cities:
        return jsonify({"error": f"Invalid city selection: {', '.join(invalid_cities)}"}), 400

    try:
        route_result = compute_route(waypoints, algorithm)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(serialize_route(src, dst, stops, algorithm, route_result))


@app.route("/metrics")
def get_metrics():
    return jsonify(calculate_network_metrics())


@app.route("/compare-algorithms", methods=["POST"])
def compare_algorithms():
    src, dst, stops, _ = parse_route_request()

    if not src or not dst:
        return jsonify({"error": "Source and destination are required."}), 400

    waypoints = [src] + stops + [dst]
    invalid_cities = validate_waypoints(waypoints)
    if invalid_cities:
        return jsonify({"error": f"Invalid city selection: {', '.join(invalid_cities)}"}), 400

    try:
        start = time.perf_counter()
        dijkstra_result = compute_route(waypoints, "dijkstra")
        dijkstra_time = round((time.perf_counter() - start) * 1000, 3)

        start = time.perf_counter()
        floyd_result = compute_route(waypoints, "floyd_warshall")
        floyd_time = round((time.perf_counter() - start) * 1000, 3)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "dijkstra": {
            "distance": dijkstra_result["distance"],
            "path": dijkstra_result["path"],
            "time_ms": dijkstra_time,
        },
        "floyd_warshall": {
            "distance": floyd_result["distance"],
            "path": floyd_result["path"],
            "time_ms": floyd_time,
        },
        "same_result": math.isclose(dijkstra_result["distance"], floyd_result["distance"]),
    })


if __name__ == "__main__":
    print(
        "\n"
        "========================================================\n"
        " Indian Road Trip Planner\n"
        " Dijkstra + Floyd-Warshall route service\n"
        " Server: http://127.0.0.1:5000\n"
        "========================================================\n"
    )
    app.run(debug=True, host="0.0.0.0", port=5000)
