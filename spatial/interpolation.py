import json
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.interpolate import griddata
from shapely.geometry import Point
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')  # backend non-interactif, pas de fenêtre GUI

# Palette AQI standard
AQI_COLORS = [
    (0,   "#00E400"),   # Bon
    (51,  "#FFFF00"),   # Modéré
    (101, "#FF7E00"),   # Mauvais GS
    (151, "#FF0000"),   # Mauvais
    (201, "#8F3F97"),   # Très mauvais
    (301, "#7E0023"),   # Dangereux
]

def aqi_colormap():
    """Construit un colormap matplotlib depuis la palette AQI."""
    hex_colors = [
        "#00E400",  # 0-50 Bon
        "#FFFF00",  # 51-100 Modéré
        "#FF7E00",  # 101-150 Mauvais GS
        "#FF0000",  # 151-200 Mauvais
        "#8F3F97",  # 201-300 Très mauvais
        "#7E0023",  # 301+ Dangereux
    ]
    rgb_colors = [mcolors.hex2color(h) for h in hex_colors]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "aqi",
        rgb_colors,  # from_list accepte directement une liste de couleurs
        N=256
    )
    return cmap

def generate_idw_image(stations, output_png, output_bounds, resolution=500, power=2):
    """
    Génère un PNG interpolé IDW depuis une liste de stations.
    
    Paramètres
    ----------
    stations    : liste de dicts {name, lat, lon, aqi}
    output_png  : chemin du PNG de sortie
    output_bounds : chemin du JSON bounds (pour OpenLayers)
    resolution  : taille de la grille d'interpolation (resolution x resolution)
    power       : exposant IDW (2 = standard)
    """
    if len(stations) < 3:
        print("Pas assez de stations pour interpoler.")
        return

    # --- 1. Construire le GeoDataFrame des stations ---
    gdf = gpd.GeoDataFrame(
        stations,
        geometry=[Point(s["lon"], s["lat"]) for s in stations],
        crs="EPSG:4326"
    )

    lons = gdf.geometry.x.values
    lats = gdf.geometry.y.values
    aqis = gdf["aqi"].values.astype(float)

    # --- 2. Définir l'étendue géographique ---
    lon_min, lon_max = lons.min() - 0.5, lons.max() + 0.5
    lat_min, lat_max = lats.min() - 0.5, lats.max() + 0.5

    # --- 3. Créer la grille d'interpolation ---
    grid_lon, grid_lat = np.meshgrid(
        np.linspace(lon_min, lon_max, resolution),
        np.linspace(lat_min, lat_max, resolution)
    )

    # --- 4. IDW manuel (Scipy griddata = linéaire/cubique, on fait IDW à la main) ---
    points = np.column_stack([lons, lats])
    grid_points = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])

    # Calcul des distances entre chaque point de grille et chaque station
    diff = grid_points[:, np.newaxis, :] - points[np.newaxis, :, :]  # (N_grid, N_stations, 2)
    distances = np.sqrt((diff ** 2).sum(axis=2))                      # (N_grid, N_stations)

    # Éviter la division par zéro (point exactement sur une station)
    distances = np.where(distances == 0, 1e-10, distances)

    weights = 1.0 / (distances ** power)                              # IDW weights
    weighted_sum = (weights * aqis[np.newaxis, :]).sum(axis=1)
    weight_total = weights.sum(axis=1)
    grid_aqi = (weighted_sum / weight_total).reshape(resolution, resolution)

    # --- 5. Appliquer le colormap AQI ---
    cmap = aqi_colormap()
    norm = mcolors.Normalize(vmin=0, vmax=300)

    fig, ax = plt.subplots(figsize=(resolution/100, resolution/100), dpi=100)
    ax.imshow(
        grid_aqi,
        origin="upper",
        extent=[lon_min, lon_max, lat_min, lat_max],
        cmap=cmap,
        norm=norm,
        alpha=0.65,
        interpolation="bilinear"
    )
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(output_png, bbox_inches="tight", pad_inches=0, transparent=True, dpi=100)
    plt.close()

    # --- 6. Sauvegarder les bounds pour OpenLayers ---
    bounds = {
        "lon_min": lon_min,
        "lon_max": lon_max,
        "lat_min": lat_min,
        "lat_max": lat_max
    }
    with open(output_bounds, "w") as f:
        json.dump(bounds, f)

    print(f"IDW généré : {len(stations)} stations, grille {resolution}×{resolution}")