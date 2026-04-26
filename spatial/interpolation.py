import matplotlib
matplotlib.use('Agg')

import os
import json
import urllib.request
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import warnings
warnings.filterwarnings("ignore")

AQI_THRESHOLDS = [0, 50, 100, 150, 200, 300]
AQI_COLORS = [
    "#00E400",  # 0-50   Bon
    "#FFFF00",  # 51-100  Modéré
    "#FF7E00",  # 101-150 Mauvais GS
    "#FF0000",  # 151-200 Mauvais
    "#8F3F97",  # 201-300 Très mauvais
    "#7E0023",  # 301+    Dangereux
]

def aqi_to_color(aqi):
    """Retourne la couleur AQI standard pour une valeur donnée."""
    for i, threshold in enumerate(reversed(AQI_THRESHOLDS)):
        if aqi >= threshold:
            return AQI_COLORS[len(AQI_THRESHOLDS) - 1 - i]
    return AQI_COLORS[0]

def get_world_geodataframe():
    """Télécharge et retourne le GeoDataFrame Natural Earth pays."""
    cache_path = os.path.join(os.path.dirname(__file__), "naturalearth_lowres.gpkg")
    if not os.path.exists(cache_path):
        print("Téléchargement Natural Earth...")
        url = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"
        zip_path = cache_path + ".zip"
        urllib.request.urlretrieve(url, zip_path)
        world = gpd.read_file(f"zip://{zip_path}")
        world = world[["NAME", "ISO_A3", "geometry"]].rename(
            columns={"NAME": "name", "ISO_A3": "iso_a3"}
        )
        world.to_file(cache_path, driver="GPKG")
        os.remove(zip_path)
        print("Natural Earth téléchargé et mis en cache.")
    else:
        world = gpd.read_file(cache_path)
    return world

def generate_country_geojson(stations, output_geojson):
    """
    Jointure spatiale stations AQICN × polygones pays (Natural Earth).
    Calcule l'AQI moyen par pays via GeoPandas et exporte un GeoJSON coloré.

    Paramètres
    ----------
    stations       : liste de dicts {name, lat, lon, aqi}
    output_geojson : chemin du GeoJSON de sortie
    """
    if len(stations) < 1:
        print("Pas de stations disponibles.")
        return

    # --- 1. GeoDataFrame des stations ---
    gdf_stations = gpd.GeoDataFrame(
        stations,
        geometry=[Point(s["lon"], s["lat"]) for s in stations],
        crs="EPSG:4326"
    )

    # --- 2. Polygones pays Natural Earth ---
    world = get_world_geodataframe()

    # --- 3. Jointure spatiale : associer chaque station à son pays ---
    joined = gpd.sjoin(
        gdf_stations,
        world[["name", "iso_a3", "geometry"]],
        how="left",
        predicate="within"
    )

    # --- 4. Agrégation : AQI moyen + nb stations par pays ---
    stats = (
        joined
        .dropna(subset=["iso_a3"])
        .groupby("iso_a3")
        .agg(
            aqi_mean=("aqi", "mean"),
            aqi_min=("aqi", "min"),
            aqi_max=("aqi", "max"),
            station_count=("aqi", "count")
        )
        .reset_index()
    )
    stats["aqi_mean"] = stats["aqi_mean"].round(1)

    # --- 5. Fusion avec les polygones pays ---
    world_aqi = world.merge(stats, on="iso_a3", how="left")

    # --- 6. Colorisation ---
    def style_country(row):
        if pd.isna(row["aqi_mean"]):
            return None
        return aqi_to_color(row["aqi_mean"])

    world_aqi["color"] = world_aqi.apply(style_country, axis=1)
    world_aqi["aqi_mean"] = world_aqi["aqi_mean"].fillna(-1)
    world_aqi["station_count"] = world_aqi["station_count"].fillna(0).astype(int)

    # --- 7. Export GeoJSON (pays avec données uniquement) ---
    world_with_data = world_aqi[world_aqi["color"].notna()].copy()
    world_with_data = world_with_data.to_crs("EPSG:4326")
    geojson_data = json.loads(world_with_data.to_json())

    with open(output_geojson, "w") as f:
        json.dump(geojson_data, f)

    print(f"GeoJSON pays généré : {len(world_with_data)} pays avec données, "
          f"{len(stations)} stations traitées")