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
    "Tunjuelito": {"lat": 4.5730, "lon": -74.13
