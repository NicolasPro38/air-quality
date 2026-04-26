import matplotlib
matplotlib.use('Agg')

import os
import json
import time
import threading
import requests
from flask import Flask, jsonify, render_template, send_file
from dotenv import load_dotenv
from spatial.interpolation import generate_country_geojson

app = Flask(__name__)
load_dotenv()

AQICN_TOKEN = os.getenv("AQICN_TOKEN")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "static", "cache")
CACHE_DURATION = 3600

TILES = [
    (-90, -180, -30,   0),
    (-90,    0, -30, 180),
    (-30, -180,  20, -60),
    (-30,  -60,  20,   0),
    (-30,    0,  20,  60),
    (-30,   60,  20, 120),
    (-30,  120,  20, 180),
    ( 20, -180,  50, -90),
    ( 20,  -90,  50,   0),
    ( 20,    0,  35,  30),
    ( 20,   30,  35,  60),
    ( 35,    0,  50,  30),
    ( 35,   30,  50,  60),
    ( 20,   60,  35,  90),
    ( 20,   90,  35, 120),
    ( 35,   60,  50,  90),
    ( 35,   90,  50, 120),
    ( 20,  120,  50, 180),
    ( 50, -180,  90,   0),
    ( 50,    0,  90,  90),
    ( 50,   90,  90, 180),
]

def fetch_stations():
    seen = set()
    stations = []
    for (lat1, lon1, lat2, lon2) in TILES:
        url = (f"https://api.waqi.info/map/bounds/"
               f"?latlng={lat1},{lon1},{lat2},{lon2}&token={AQICN_TOKEN}")
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("status") != "ok":
                continue
            for s in data["data"]:
                try:
                    uid = s["uid"]
                    if uid in seen:
                        continue
                    seen.add(uid)
                    aqi = int(s["aqi"])
                    stations.append({
                        "name": s["station"]["name"],
                        "lat": float(s["lat"]),
                        "lon": float(s["lon"]),
                        "aqi": aqi
                    })
                except (ValueError, KeyError):
                    continue
        except Exception as e:
            print(f"Erreur tuile {lat1},{lon1}: {e}")
    print(f"Total stations récupérées : {len(stations)}")
    return stations

def refresh_cache():
    stations = fetch_stations()
    if not stations:
        return
    with open(os.path.join(CACHE_DIR, "stations.json"), "w") as f:
        json.dump({"stations": stations, "timestamp": time.time()}, f)
    generate_country_geojson(
        stations,
        os.path.join(CACHE_DIR, "countries.geojson")
    )

def auto_refresh():
    while True:
        try:
            refresh_cache()
        except Exception as e:
            print(f"Erreur auto_refresh: {e}")
        time.sleep(CACHE_DURATION)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stations")
def api_stations():
    path = os.path.join(CACHE_DIR, "stations.json")
    if os.path.exists(path):
        with open(path) as f:
            return jsonify(json.load(f))
    stations = fetch_stations()
    return jsonify({"stations": stations, "timestamp": time.time()})

@app.route("/api/countries")
def api_countries():
    path = os.path.join(CACHE_DIR, "countries.geojson")
    if not os.path.exists(path):
        refresh_cache()
    with open(path) as f:
        return jsonify(json.load(f))

_cache_initialized = False

@app.before_request
def init_cache():
    global _cache_initialized
    if not _cache_initialized:
        _cache_initialized = True
        if not os.path.exists(os.path.join(CACHE_DIR, "countries.geojson")):
            threading.Thread(target=refresh_cache, daemon=True).start()

if __name__ == "__main__":
    os.makedirs(CACHE_DIR, exist_ok=True)
    refresh_cache()
    t = threading.Thread(target=auto_refresh, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5007, debug=False)