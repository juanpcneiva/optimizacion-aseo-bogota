import os
import time
import osmnx as ox
import networkx as nx
from red_bogota import (
    CARPETA_CACHE,
    LOCALIDADES_BOGOTA,
    RADIOS_DISPONIBLES,
    _limpiar_nombre,
    _recortar_grafo_por_radio,
    construir_grafo_macro_bogota,
    descargar_sector_localidad,
    obtener_ruta_vial_real_dona_juana
)


def generar_todo_el_cache():
    os.makedirs(CARPETA_CACHE, exist_ok=True)
    G_macro = construir_grafo_macro_bogota()

    localidades = [loc for loc in LOCALIDADES_BOGOTA.keys() if loc != "Relleno Doña Juana"]
    print(f"Iniciando generacion de cache para {len(localidades)} localidades y {len(RADIOS_DISPONIBLES)} distancias...")

    for idx, loc in enumerate(localidades, start=1):
        nombre_limpio = _limpiar_nombre(loc)
        info = LOCALIDADES_BOGOTA[loc]
        lat_c, lon_c = info["lat"], info["lon"]

        print(f"\n[{idx}/{len(localidades)}] Procesando localidad: {loc}")

        # 1. Asegurar grafo maestro de 1000m
        try:
            G_1000 = descargar_sector_localidad(loc, radio_metros=1000)
            archivo_1000 = os.path.join(CARPETA_CACHE, f"{nombre_limpio}_1000m.graphml")
            if not os.path.exists(archivo_1000):
                ox.save_graphml(G_1000, archivo_1000)
            print(f"  -> Grafo maestro 1000m listo ({len(G_1000.nodes)} nodos, {len(G_1000.edges)} aristas)")
        except Exception as e:
            print(f"  [ERROR] No se pudo obtener el grafo de 1000m para {loc}: {e}")
            continue

        # 2. Generar y guardar cada distancia del slider (350m a 950m)
        for radio in RADIOS_DISPONIBLES:
            archivo_radio = os.path.join(CARPETA_CACHE, f"{nombre_limpio}_{radio}m.graphml")
            if radio == 1000 and os.path.exists(archivo_radio):
                continue
            try:
                G_sub = _recortar_grafo_por_radio(G_1000, lat_c, lon_c, radio)
                ox.save_graphml(G_sub, archivo_radio)
                print(f"  -> Guardado {nombre_limpio}_{radio}m.graphml ({len(G_sub.nodes)} nodos)")
            except Exception as e:
                print(f"  [ERROR] Fallo en radio {radio}m para {loc}: {e}")

        # 3. Generar ruta macro OSRM hacia Doña Juana
        try:
            ruta_nodos = nx.dijkstra_path(G_macro, source=loc, target="Relleno Doña Juana", weight="distancia_km")
             _, dist_km, _ = obtener_ruta_vial_real_dona_juana(ruta_nodos, lat_c, lon_c)
            print(f"  -> Ruta Dona Juana guardada ({dist_km} km)")
        except Exception as e:
            print(f"  [ERROR] Fallo en ruta OSRM para {loc}: {e}")

        time.sleep(0.5)

    print("\nProceso completado exitosamente.")


if __name__ == "__main__":
    generar_todo_el_cache()
