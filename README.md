# 🌍 Air Quality Map

Carte mondiale interactive de la qualité de l'air, construite avec Flask, GeoPandas et OpenLayers.

## Aperçu

![Air Quality Map](https://cartonicolasrey.duckdns.org/air-quality/)

L'application récupère en temps réel les données de 4 600+ stations de mesure mondiales via l'API AQICN, puis effectue une **jointure spatiale GeoPandas** pour calculer l'AQI moyen par pays et générer une choroplèthe mondiale.

## Fonctionnalités

- **Choroplèthe pays** : AQI moyen calculé par jointure spatiale `gpd.sjoin()` entre les stations et les polygones Natural Earth
- **4 600+ stations** récupérées par découpage en tuiles pour contourner la limite de l'API
- **Mise à jour horaire** automatique via cron
- **Toggle couches** : affichage indépendant de la choroplèthe et des stations
- **Popup interactif** : détail AQI par station et par pays au clic
- **Opacité réglable** de la couche choroplèthe

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python · Flask · Gunicorn |
| Analyse spatiale | GeoPandas · Shapely |
| Données géographiques | Natural Earth 50m |
| Frontend | OpenLayers 8 |
| Déploiement | VPS OVH · Ubuntu 22.04 · Apache |
| Données | AQICN API |

## Architecture
API AQICN (tuiles mondiales)
↓
fetch_stations() — 4 650+ stations
↓
GeoPandas GeoDataFrame
↓
gpd.sjoin() × Natural Earth pays
↓
groupby() → AQI moyen par pays
↓
Export GeoJSON → OpenLayers

## Analyse spatiale (GeoPandas)

Le cœur de l'application est dans `spatial/interpolation.py` :

```python
# Jointure spatiale stations × polygones pays
joined = gpd.sjoin(gdf_stations, world, how="left", predicate="within")

# Agrégation statistique par pays
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
```

## Installation locale

```bash
git clone https://github.com/NicolasPro38/air-quality.git
cd air-quality
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Créer le fichier .env
echo "AQICN_TOKEN=votre_token" > .env
# Obtenir un token gratuit sur https://aqicn.org/data-platform/token/

python3 app.py
# → http://localhost:5007
```

## Démo

🌐 [cartonicolasrey.duckdns.org/air-quality](https://cartonicolasrey.duckdns.org/air-quality/)

## Données

- **Stations** : [AQICN API](https://aqicn.org/api/) — données temps réel, mise à jour horaire
- **Polygones pays** : [Natural Earth](https://www.naturalearthdata.com/) — 50m, domaine public

## Auteur

**Nicolas Rey Romano** — Géomaticien  
[Portfolio](https://cartonicolasrey.duckdns.org/portfolio/) · [LinkedIn](https://www.linkedin.com/in/nicolas-rey-5898b3116/) · [GitHub](https://github.com/NicolasPro38)