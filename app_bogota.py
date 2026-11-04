"""
================================================================================
MÓDULO 3: DASHBOARD SATELITAL INTERACTIVO - BOGOTÁ D.C.
================================================================================
Ejecución en terminal de Anaconda:
    streamlit run app_bogota.py
================================================================================
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

from red_bogota import LOCALIDADES_BOGOTA, construir_grafo_macro_bogota, descargar_sector_localidad
from teoria_algoritmos import (
    extraer_componente_fuertemente_conexa,
    analizar_desbalance_grados,
    eulerizar_grafo_min_cost_flow,
    algoritmo_hierholzer_propio,
    dijkstra_macro_dona_juana
)

st.set_page_config(page_title="Teoría de Grafos - Aseo Bogotá", layout="wide")

st.title("🛰️ Optimización de Recolección de Basuras en Bogotá D.C.")
st.markdown("**Aplicación Real de Teoría de Grafos:** *Algoritmo de Tarjan (SCC) + Flujo de Costo Mínimo + Algoritmo de Hierholzer (DCPP) + Dijkstra Macro*")

# --- BARRA LATERAL DE CONTROL ---
st.sidebar.header("⚙️ Parámetros de Operación en Bogotá")

lista_localidades = [loc for loc in LOCALIDADES_BOGOTA.keys() if loc != "Relleno Doña Juana"]
localidad_sel = st.sidebar.selectbox("1. Selecciona la Localidad de Bogotá:", lista_localidades, index=12)

radio_m = st.sidebar.slider("2. Radio del cuadrante operativo (metros):", min_value=350, max_value=1200, value=600, step=50)

tipo_mapa = st.sidebar.radio(
    "3. Capa de Visualización Geoespacial:",
    ["Satelital Híbrido (Esri World Imagery + Vías)", "OpenStreetMap Estándar"]
)

mostrar_nodos = st.sidebar.checkbox("Mostrar nodos desbalanceados (Fuentes/Sumideros)", value=True)
mostrar_macro = st.sidebar.checkbox("Mostrar Ruta Macro hacia Relleno Doña Juana (Dijkstra)", value=True)

# --- PROCESAMIENTO DE GRAFOS ---
with st.spinner(f"Procesando topología vial de {localidad_sel} y resolviendo modelo matemático..."):
    # 1. Nivel Macro (Bogotá completa -> Doña Juana)
    G_macro = construir_grafo_macro_bogota()
    ruta_macro, dist_dona_juana = dijkstra_macro_dona_juana(G_macro, localidad_sel)

    # 2. Nivel Micro (Descarga y Tarjan SCC)
    G_raw = descargar_sector_localidad(localidad_sel, radio_metros=radio_m)
    G_scc, num_scc = extraer_componente_fuertemente_conexa(G_raw)

    # 3. Análisis de grados y Flujo de Costo Mínimo
    demandas, resumen_grados = analizar_desbalance_grados(G_scc)
    G_euler, aristas_dup = eulerizar_grafo_min_cost_flow(G_scc, demandas)

    # 4. Algoritmo de Hierholzer propio
    secuencia_tramos, dist_total_m, dist_rep_m = algoritmo_hierholzer_propio(G_euler)

dist_neta_km = (dist_total_m - dist_rep_m) / 1000.0
dist_total_km = dist_total_m / 1000.0
dist_muerta_km = dist_rep_m / 1000.0
eficiencia = (dist_neta_km / dist_total_km) * 100 if dist_total_km > 0 else 0

# --- PANEL DE MÉTRICAS (KPIs) ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Localidad / Operador", localidad_sel, LOCALIDADES_BOGOTA[localidad_sel]["ase"])
col2.metric("Intersecciones | Vías", f"{resumen_grados['total_nodos']} | {resumen_grados['total_aristas']}", f"{aristas_dup} vías repetidas")
col3.metric("Recorrido Micro (DCPP)", f"{dist_total_km:.2f} km", f"{dist_muerta_km:.2f} km tránsito muerto")
col4.metric("Eficiencia Euleriana", f"{eficiencia:.1f}%", "Óptimo global garantizado")
col5.metric("Ruta a Doña Juana (Dijkstra)", f"{dist_dona_juana} km", f"{len(ruta_macro)-1} tramos arteriales")

# --- PESTAÑAS: MAPA SATELITAL, TEORÍA EN VIVO Y BITÁCORA ---
tab_mapa, tab_teoria, tab_tabla = st.tabs([
    "🛰️ Mapa Satelital Interactivo (Micro y Macro)",
    "📐 Demostración Matemática y Teoría Aplicada",
    "📋 Secuencia Paso a Paso del Camión (Hierholzer)"
])

with tab_mapa:
    lat_c = LOCALIDADES_BOGOTA[localidad_sel]["lat"]
    lon_c = LOCALIDADES_BOGOTA[localidad_sel]["lon"]

    # Crear mapa base sin marcas de agua
    mapa = folium.Map(location=[lat_c, lon_c], zoom_start=15, tiles=None)

    if "Satelital" in tipo_mapa:
        # Capa Satelital de Alta Resolución Esri World Imagery (Gratuita y sin API Key)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="Satelital Esri",
            overlay=False,
            control=True
        ).add_to(mapa)
        # Capa superpuesta con nombres de calles y avenidas de Bogotá
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Transportation",
            name="Nombres de Vías",
            overlay=True,
            control=True
        ).add_to(mapa)
    else:
        folium.TileLayer("OpenStreetMap", name="Mapa Callejero").add_to(mapa)

    # 1. Dibujar malla vial original del sector
    for u, v, data in G_scc.edges(data=True):
        if "geometry" in data:
            coords = [(pt[1], pt[0]) for pt in data["geometry"].coords]
        else:
            coords = [(G_scc.nodes[u]["y"], G_scc.nodes[u]["x"]), (G_scc.nodes[v]["y"], G_scc.nodes[v]["x"])]
        folium.PolyLine(coords, color="#ffffff", weight=2, opacity=0.45).add_to(mapa)

    # 2. Dibujar el circuito Euleriano óptimo (Cian brillante para alto contraste en vista satelital)
    coords_circuito = []
    for paso in secuencia_tramos:
        u = paso["origen"]
        coords_circuito.append((G_scc.nodes[u]["y"], G_scc.nodes[u]["x"]))
    ultimo_destino = secuencia_tramos[-1]["destino"]
    coords_circuito.append((G_scc.nodes[ultimo_destino]["y"], G_scc.nodes[ultimo_destino]["x"]))

    folium.PolyLine(
        coords_circuito,
        color="#00f2fe",
        weight=4.5,
        opacity=0.9,
        tooltip=f"Circuito Euleriano {localidad_sel}: {dist_total_km:.2f} km"
    ).add_to(mapa)

    # 3. Dibujar nodos desbalanceados (Fuentes en Rojo, Sumideros en Amarillo)
    if mostrar_nodos:
        for n, b_v in demandas.items():
            if b_v != 0:
                color_nodo = "#ff3b30" if b_v < 0 else "#ffcc00"
                tipo_txt = "Fuente (Exceso Entrada)" if b_v < 0 else "Sumidero (Exceso Salida)"
                folium.CircleMarker(
                    location=[G_scc.nodes[n]["y"], G_scc.nodes[n]["x"]],
                    radius=4,
                    color=color_nodo,
                    fill=True,
                    fill_opacity=0.9,
                    popup=f"Nodo ID: {n}<br>Tipo: {tipo_txt}<br>Demanda b(v) = {b_v}"
                ).add_to(mapa)

    # 4. Dibujar Ruta Macro hacia Relleno Doña Juana
    if mostrar_macro:
        coords_macro = [
            (LOCALIDADES_BOGOTA[loc]["lat"], LOCALIDADES_BOGOTA[loc]["lon"])
            for loc in ruta_macro
        ]
        folium.PolyLine(
            coords_macro,
            color="#ff9500",
            weight=5,
            dash_array="10, 10",
            tooltip=f"Ruta Macro Dijkstra a Doña Juana ({dist_dona_juana} km): {' -> '.join(ruta_macro)}"
        ).add_to(mapa)

        # Marcador en Relleno Doña Juana
        dj = LOCALIDADES_BOGOTA["Relleno Doña Juana"]
        folium.Marker(
            [dj["lat"], dj["lon"]],
            popup="<b>Relleno Sanitario Doña Juana</b><br>Nodo Sumidero Distrital",
            icon=folium.Icon(color="darkred", icon="dumpster", prefix="fa")
        ).add_to(mapa)

    # Marcador de inicio del camión en la localidad
    nodo_0 = secuencia_tramos[0]["origen"]
    folium.Marker(
        [G_scc.nodes[nodo_0]["y"], G_scc.nodes[nodo_0]["x"]],
        popup=f"<b>Base Operativa {localidad_sel}</b><br>Inicio y Fin del Circuito Euleriano",
        icon=folium.Icon(color="green", icon="truck", prefix="fa")
    ).add_to(mapa)

    # Botón para exportar tu HTML satelital independiente
    html_string = mapa.get_root().render()
    st.download_button(
        label="💾 Descargar este Mapa Satelital como archivo HTML independiente",
        data=html_string,
        file_name=f"mapa_satelital_{localidad_sel.lower().replace(' ', '_')}.html",
        mime="text/html"
    )

    st_folium(mapa, width=1300, height=620)

with tab_teoria:
    st.subheader("Sustentación Matemática Calculada en Tiempo Real sobre el Grafo Actual")
    st.markdown(f"""
    #### 1. Filtrado Topológico por Conectividad Fuerte (Algoritmo de Tarjan)
    En la descarga bruta de **{localidad_sel}** se identificaron **{num_scc} componentes conexas**. 
    Para garantizar que el camión compactador siempre pueda regresar al punto de partida sin quedar atrapado en vías cerradas, se extrajo el subgrafo maximal $G_{{SCC}} = (V, E)$ con:
    * $|V| = {resumen_grados['total_nodos']}$ vértices (intersecciones viales).
    * $|E| = {resumen_grados['total_aristas']}$ aristas dirigidas (segmentos de vía con sentido).

    ---
    #### 2. Verificación del Teorema de Euler y Desbalance de Grados
    Para cada esquina $v \in V$ se calculó el balance $\\text{{demanda}}(v) = \\text{{deg}}^+(v) - \\text{{deg}}^-(v)$:
    * **Nodos Balanceados ($\\text{{deg}}^+(v) = \\text{{deg}}^-(v)$):** `{resumen_grados['balanceados']}` intersecciones.
    * **Nodos Fuente ($\\text{{deg}}^-(v) > \\text{{deg}}^+(v)$):** `{resumen_grados['fuentes']}` intersecciones (puntos rojos en el mapa).
    * **Nodos Sumidero ($\\text{{deg}}^+(v) > \\text{{deg}}^-(v)$):** `{resumen_grados['sumideros']}` intersecciones (puntos amarillos en el mapa).

    ---
    #### 3. Eulerización por Flujo de Costo Mínimo (Network Simplex)
    Se resolvió el problema de optimización lineal:
    $$\\min \\sum_{{e \\in E}} w(e) \\cdot f(e) \\quad \\text{{sujeto a}} \\quad \\sum f(\\text{{entrantes}}) - \\sum f(\\text{{salientes}}) = \\text{{deg}}^+(v) - \\text{{deg}}^-(v)$$
    * **Resultado de la optimización:** Se duplicaron exactamente **`{aristas_dup}` aristas** (agregando `{dist_muerta_km:.2f} km` de recorrido de enlace), logrando que $\\text{{is\_eulerian}}(G_{{euler}}) = \\text{{True}}$.

    ---
    #### 4. Ruta Macro de Disposición Final hacia Doña Juana (Algoritmo de Dijkstra)
    Una vez lleno el camión en **{localidad_sel}**, la trayectoria de costo mínimo sobre el grafo arterial de Bogotá hacia el Relleno Sanitario Doña Juana es:
    * **Secuencia de localidades:** `{" ➔ ".join(ruta_macro)}`
    * **Distancia arterial acumulada:** `{dist_dona_juana} km`
    """)

with tab_tabla:
    st.subheader(f"Hoja de Ruta Secuencial Generada por tu Algoritmo de Hierholzer ({len(secuencia_tramos)} tramos)")
    df_ruta = pd.DataFrame(secuencia_tramos)
    st.dataframe(df_ruta, use_container_width=True, height=450)