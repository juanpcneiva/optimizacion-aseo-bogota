import os
import time
from red_bogota import (
    LOCALIDADES_BOGOTA,
    CARPETA_CACHE,
    construir_grafo_macro_bogota,
    descargar_sector_localidad,
    obtener_ruta_vial_real_dona_juana
)
from teoria_algoritmos import dijkstra_macro_dona_juana

def main():
    G_macro = construir_grafo_macro_bogota()
    localidades = [k for k in LOCALIDADES_BOGOTA.keys() if k != "Relleno Doña Juana"]

    print(f"=== INICIANDO DESCARGA A 1000M ({len(localidades)} LOCALIDADES) ===")
    for i, loc in enumerate(localidades, 1):
        print(f"[{i}/{len(localidades)}] Descargando {loc}...")
        try:
            descargar_sector_localidad(loc, radio_metros=1000)
            ruta_macro, _ = dijkstra_macro_dona_juana(G_macro, loc)
            info = LOCALIDADES_BOGOTA[loc]
            obtener_ruta_vial_real_dona_juana(ruta_macro, info["lat"], info["lon"])
            print(f"  -> {loc} guardada correctamente.")
            time.sleep(1.2)
        except Exception as e:
            print(f"  -> Advertencia en {loc}: {e}")

    # Eliminar temporales intermedios de OpenStreetMap dejando solo los grafos y rutas
    for f in os.listdir(CARPETA_CACHE):
        if f.endswith(".json") and not f.startswith("ruta_dj_"):
            try:
                os.remove(os.path.join(CARPETA_CACHE, f))
            except Exception:
                pass

    print("=== PROCESO COMPLETADO EXITOSAMENTE ===")

if __name__ == "__main__":
    main()
