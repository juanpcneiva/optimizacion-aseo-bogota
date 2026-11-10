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

# Ruta absoluta al directorio actual (garantiza compatibilidad en Windows, Linux y Streamlit Cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_CACHE = os.path.join(BASE_DIR, "cache_bogota")
os.makedirs(CARPETA_CACHE, exist_ok=True)

# Configuración del motor OSMnx
ox.settings.use_cache = True
ox.settings.cache_folder = CARPETA_CACHE
ox.settings.timeout = 180
ox.settings.overpass_rate_limit = False

# Servidores espejo de alta disponibilidad tolerantes a conexiones desde Streamlit Cloud / AWS
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
