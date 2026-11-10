"""
================================================================================
MÓDULO 2: MODELADO MULTIESCALA DE BOGOTÁ D.C. Y RUTEO VIAL REAL A DOÑA JUANA
================================================================================
"""

import os
import json
import time
import requests
import osmnx as ox
import networkx as nx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_CACHE = os.path.join(BASE_DIR, "cache_bogota")
os.makedirs(CARPETA_CACHE, exist_ok=True)

ox.settings.use_cache = True
ox.settings.cache_folder = CARPETA_CACHE
ox.settings.timeout = 180
ox.settings.overpass_rate_limit = False

SERVIDORES_OVERPASS = [
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
    "https://lz4.overpass-api.de/api",
    "https://overpass.osm.ch/api"
]

LOCALIDADES_BOGOTA = {
    "Usaquén": {"lat": 4.6950, "lon": -74.0310, "ase": "Promoambiental"},
    "Chapinero": {"lat": 4.6450, "lon": -74.0610, "ase": "Promoambiental"},
    "Santa Fe": {"lat": 4.6070, "lon": -74.0690, "ase": "Promoambiental"},
    "San Cristóbal": {"lat": 4.5680, "lon": -74.0830, "ase": "Promoambiental"},
    "Usme": {"lat": 4.5080, "lon": -74.1130, "ase": "Promoambiental"},
    "Tunjuelito": {"lat": 4.5730, "lon": -74.1330, "ase": "LIME"},
    "Bosa": {"lat": 4.6210, "lon": -74.1910, "ase": "LIME"},
    "Kennedy": {"lat": 4.6280, "lon": -74.1520, "ase": "LIME"},
    "Fontibón": {"lat": 4.6730, "lon": -74.1440, "ase": "Ciudad Limpia"},
    "Engativá": {"lat": 4.7010, "lon": -74.1130, "ase": "Bogotá Limpia"},
    "Suba": {"lat": 4.7410, "lon": -74.0840, "ase": "Área Limpia"},
    "Barrios Unidos": {"lat": 4.6690, "lon": -74.0740, "ase": "Bogotá Limpia"},
    "Teusaquillo": {"lat": 4.6295, "lon": -74.0755, "ase": "LIME"},
    "Los Mártires": {"lat": 4.6050, "lon": -74.0860, "ase": "LIME"},
    "Antonio Nariño": {"lat": 4.5880, "lon": -74.1030, "ase": "LIME"},
    "Puente Aranda": {"lat": 4.6160, "lon": -74.1140, "ase": "LIME"},
    "La Candelaria": {"lat": 4.5960, "lon": -74.0730, "ase": "Promoambiental"},
    "Rafael Uribe Uribe": {"lat": 4.5660, "lon": -74.1140, "ase": "LIME"},
    "Ciudad Bolívar": {"lat": 4.5480, "lon": -74.1520, "ase": "LIME"},
    "Relleno Doña Juana": {"lat": 4.4920, "lon": -74.1410, "ase": "Disposición Final"}
}

CORREDORES_BOGOTA = [
    ("Suba", "Usaquén", 6.8, "Calle 170 / Autopista Norte"),
    ("Suba", "Engativá", 5.9, "Av. Cali / Av. Boyacá"),
    ("Usaquén", "Chapinero", 6.2, "Autopista Norte / Cra 7"),
    ("Usaquén", "Barrios Unidos", 5.5, "Autopista Norte / NQS"),
    ("Engativá", "Barrios Unidos", 4.8, "Av. Calle 80"),
    ("Engativá", "Fontibón", 4.2, "Av. Rojas / Av. Boyacá"),
    ("Barrios Unidos", "Teusaquillo", 4.5, "Av. NQS"),
    ("Chapinero", "Teusaquillo", 2.8, "Calle 45 / Av. Caracas"),
    ("Chapinero", "Santa Fe", 4.4, "Av. Circunvalar / Cra 7"),
    ("Teusaquillo", "Puente Aranda", 4.3, "Av. NQS / Av. Américas"),
    ("Teusaquillo", "Los Mártires", 3.1, "Av. NQS / Av. Caracas"),
    ("Santa Fe", "La Candelaria", 1.5, "Eje Ambiental / Cra 10"),
    ("La Candelaria", "Los Mártires", 1.8, "Av. Calle 19"),
    ("Los Mártires", "Antonio Nariño", 2.5, "Av. NQS / Cra 10"),
    ("Fontibón", "Kennedy", 5.1, "Av. Boyacá / Av. Cali"),
    ("Fontibón", "Puente Aranda", 4.9, "Av. Centenario (Calle 13)"),
    ("Puente Aranda", "Kennedy", 4.7, "Av. de las Américas"),
    ("Puente Aranda", "Antonio Nariño", 3.4, "Av. NQS Sur"),
    ("Kennedy", "Bosa", 4.8, "Av. Agoberto Mejía / Av. Villavicencio"),
    ("Kennedy", "Tunjuelito", 5.6, "Av. Boyacá Sur"),
    ("Bosa", "Ciudad Bolívar", 5.2, "Autopista Sur / Av. Villavicencio"),
    ("Antonio Nariño", "Rafael Uribe Uribe", 2.9, "Av. Caracas Sur"),
    ("Antonio Nariño", "Tunjuelito", 3.8, "Av. Boyacá / Autopista Sur"),
    ("San Cristóbal", "Rafael Uribe Uribe", 3.5, "Av. Primero de Mayo"),
    ("Rafael Uribe Uribe", "Tunjuelito", 3.1, "Av. Caracas / Calle 44 Sur"),
    ("Rafael Uribe Uribe", "Usme", 6.9, "Av. Caracas Sur / Vía al Llano"),
    ("Tunjuelito", "Ciudad Bolívar", 3.4, "Av. Villavicencio / Av. Boyacá"),
    ("Tunjuelito", "Usme", 6.5, "Av. Boyacá hacia el Sur"),
    ("Ciudad Bolívar", "Relleno Doña Juana", 6.8, "Av. Boyacá Sur - Vía Doña Juana"),
    ("Usme", "Relleno Doña Juana", 4.1, "Autopista al Llano / Acceso Doña Juana"),
    ("Tunjuelito", "Relleno Doña Juana", 9.2, "Corredor Av. Boyacá Directo")
]


def _limpiar_nombre(texto):
    reemplazos = {" ": "_", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    res = texto.lower()
    for k, v in reemplazos.items():
        res = res.replace(k, v)
    return res


def construir_grafo_macro_bogota():
    G_macro = nx.Graph()
    for nombre, info in LOCALIDADES_BOGOTA.items():
        G_macro.add_node(nombre, lat=info["lat"], lon=info["lon"], ase=info["ase"])

    for u, v, dist, via in CORREDORES_BOGOTA:
        G_macro.add_edge(u, v, distancia_km=dist, via=via)

    return G_macro


def descargar_sector_localidad(nombre_localidad, radio_metros=1000):
    nombre_limpio = _limpiar_nombre(nombre_localidad)
    archivo_exacto = os.path.join(CARPETA_CACHE, f"{nombre_limpio}_{radio_metros}m.graphml")
    archivo_fallback = os.path.join(CARPETA_CACHE, f"{nombre_limpio}_1000m.graphml")

    if os.path.exists(archivo_exacto):
        try:
            return ox.load_graphml(archivo_exacto)
        except Exception:
            pass

    if os.path.exists(archivo_fallback):
        try:
            return ox.load_graphml(archivo_fallback)
        except Exception:
            pass

    info = LOCALIDADES_BOGOTA[nombre_localidad]
    punto_central = (info["lat"], info["lon"])

    ultimo_error = None
    for _ in range(2):
        for endpoint in SERVIDORES_OVERPASS:
            try:
                ox.settings.overpass_endpoint = endpoint
                ox.settings.timeout = 75
                G_raw = ox.graph_from_point(
                    punto_central,
                    dist=radio_metros,
                    network_type="drive",
                    simplify=True
                )
                try:
                    ox.save_graphml(G_raw, archivo_exacto)
                except Exception:
                    pass
                return G_raw
            except Exception as e:
                ultimo_error = e
                time.sleep(0.8)
                continue

    raise RuntimeError(
        f"Servidores Overpass saturados temporalmente. "
        f"Verifica que la carpeta cache_bogota/ contenga los archivos de 1000m. Detalle: {ultimo_error}"
    )


def obtener_ruta_vial_real_dona_juana(ruta_macro_nodos, lat_inicio_camion, lon_inicio_camion):
    localidad_origen = ruta_macro_nodos[0]
    nombre_limpio = _limpiar_nombre(localidad_origen)
    archivo_ruta_json = os.path.join(CARPETA_CACHE, f"ruta_dj_{nombre_limpio}.json")

    if os.path.exists(archivo_ruta_json):
        try:
            with open(archivo_ruta_json, "r", encoding="utf-8") as f:
                datos_cache = json.load(f)
                return datos_cache["geometria"], datos_cache["distancia_km"], datos_cache["avenidas"]
        except Exception:
            pass

    waypoints = [(lat_inicio_camion, lon_inicio_camion)]
    for nombre_loc in ruta_macro_nodos[1:]:
        info = LOCALIDADES_BOGOTA[nombre_loc]
        waypoints.append((info["lat"], info["lon"]))

    cadena_coords = ";".join([f"{lon},{lat}" for lat, lon in waypoints])
    urls_osrm = [
        f"https://router.project-osrm.org/route/v1/driving/{cadena_coords}?overview=full&geometries=geojson&steps=true",
        f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{cadena_coords}?overview=full&geometries=geojson&steps=true"
    ]

    headers = {"User-Agent": "BogotaWasteGraphOptimizer/2.0"}
    for url in urls_osrm:
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("routes"):
                    ruta = data["routes"][0]
                    geometria_vial = [[round(pt[1], 6), round(pt[0], 6)] for pt in ruta["geometry"]["coordinates"]]
                    distancia_real_km = round(ruta["distance"] / 1000.0, 2)

                    avenidas = []
                    for leg in ruta
