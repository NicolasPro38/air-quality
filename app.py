import os
import json
import time
import threading
import requests
import numpy as np
from flask import Flask, jsonify, render_template, send_file
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

AQICN_TOKEN = os.getenv("AQICN_TOKEN")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "static", "cache")
CACHE_DURATION = 3600  # 1 heure

def fetch_stations():
    """Récupère les stations AQICN sur la France via l'API map bounds."""
    url = f"https://api.waqi.info/map/bounds/?latlng=41,−5,51,10&token={AQICN_TOKEN}"
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if data.get("status") != "ok":
        return []
    stations = []
    for s in data["data"]:
        try:
            aqi = int(s["aqi"])
            stations.append({
                "name": s["station"]["name"],
                "lat": float(s["lat"]),
                "lon": float(s["lon"]),
                "aqi": aqi
            })
        except (ValueError, KeyError):
            continue
    return stations

def refresh_cache():
    """Régénère le PNG IDW et le fichier stations en cache."""
    stations = fetch_stations()
    if not stations:
        return
    # Sauvegarder les stations en JSON
    with open(os.path.join(CACHE_DIR, "stations.json"), "w") as f:
        json.dump({"stations": stations, "timestamp": time.time()}, f)
    # Générer le PNG IDW
    generate_idw_image(stations, os.path.join(CACHE_DIR, "idw.png"),
                       os.path.join(CACHE_DIR, "bounds.json"))

def auto_refresh():
    """Thread de rafraîchissement automatique toutes les heures."""
    while True:
        try:
            refresh_cache()
        except Exception as e:
            print(f"Erreur refresh: {e}")
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
    # Pas de cache : fetch direct
    stations = fetch_stations()
    return jsonify({"stations": stations, "timestamp": time.time()})

@app.route("/api/idw.png")
def api_idw_png():
    path = os.path.join(CACHE_DIR, "idw.png")
    if not os.path.exists(path):
        refresh_cache()
    return send_file(path, mimetype="image/png")

@app.route("/api/bounds")
def api_bounds():
    path = os.path.join(CACHE_DIR, "bounds.json")
    if not os.path.exists(path):
        refresh_cache()
    with open(path) as f:
        return jsonify(json.load(f))

if __name__ == "__main__":
    # Premier chargement au démarrage
    os.makedirs(CACHE_DIR, exist_ok=True)
    refresh_cache()
    # Thread de rafraîchissement
    t = threading.Thread(target=auto_refresh, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5007, debug=True)