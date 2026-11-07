"""
================================================================================
MÓDULO 3: DASHBOARD SATELITAL CON SIMULADOR EN VIVO DEL CAMIÓN - BOGOTÁ D.C.
================================================================================
Ejecución:
    streamlit run app_bogota.py
================================================================================
"""

import json
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from red_bogota import (
    LOCALIDADES_BOGOTA,
    construir_grafo_macro_bogota,
    descargar_sector_localidad,
    obtener_ruta_vial_real_dona_juana
)
from teoria_algoritmos import (
    extraer_componente_fuertemente_conexa,
    analizar_desbalance_grados,
    eulerizar_grafo_min_cost_flow,
    algoritmo_hierholzer_propio,
    dijkstra_macro_dona_juana
)

st.set_page_config(page_title="Teoría de Grafos - Aseo Bogotá", layout="wide")

st.title("🛰️ Optimización de Recolección de Basuras en Bogotá D.C.")
st.markdown(
    "**Aplicación Real de Teoría de Grafos:** *Algoritmo de Tarjan (SCC) + "
    "Flujo de Costo Mínimo + Algoritmo de Hierholzer (DCPP) + Dijkstra Vial a Doña Juana*"
)

# ==============================================================================
# 1. MOTOR CACHEADO (EVITA RECALCULAR Y PROTEGE CONTRA ERRORES DE OVERPASS)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def calcular_modelo_completo(localidad: str, radio_m: int):
    # 1. Nivel Macro (Dijkstra en grafo de localidades)
    G_macro = construir_grafo_macro_bogota()
    ruta_macro, dist_dijkstra_km = dijkstra_macro_dona_juana(G_macro, localidad)

    # 2. Nivel Micro (Descarga de calles y Tarjan SCC)
    G_raw = descargar_sector_localidad(localidad, radio_metros=radio_m)
    G_scc, num_scc = extraer_componente_fuertemente_conexa(G_raw)

    # 3. Análisis de grados y Flujo de Costo Mínimo
    demandas, resumen_grados = analizar_desbalance_grados(G_scc)
    G_euler, aristas_dup = eulerizar_grafo_min_cost_flow(G_scc, demandas)

    # 4. Circuito Euleriano con Hierholzer propio
    secuencia_tramos, dist_total_m, dist_rep_m = algoritmo_hierholzer_propio(G_euler)

    # 5. Geometría real calle por calle hacia el Relleno Doña Juana
    nodo_inicio = secuencia_tramos[0]["origen"]
    lat_0 = G_scc.nodes[nodo_inicio]["y"]
    lon_0 = G_scc.nodes[nodo_inicio]["x"]
    coords_dona_juana, dist_vial_dj_km, avenidas_dj = obtener_ruta_vial_real_dona_juana(
        ruta_macro, lat_0, lon_0
    )
    dist_final_dj = dist_vial_dj_km if dist_vial_dj_km > 0 else dist_dijkstra_km

    # Pre-extraer malla base y nodos para renderizado instantáneo en JS
    aristas_base = []
    for u, v, data in G_scc.edges(data=True):
        if "geometry" in data:
            aristas_base.append([[round(pt[1], 6), round(pt[0], 6)] for pt in data["geometry"].coords])
        else:
            aristas_base.append([
                [round(G_scc.nodes[u]["y"], 6), round(G_scc.nodes[u]["x"], 6)],
                [round(G_scc.nodes[v]["y"], 6), round(G_scc.nodes[v]["x"], 6)]
            ])

    nodos_desbalance = []
    for n, b_v in demandas.items():
        if b_v != 0:
            nodos_desbalance.append({
                "id": n,
                "lat": round(G_scc.nodes[n]["y"], 6),
                "lon": round(G_scc.nodes[n]["x"], 6),
                "b": b_v
            })

    return {
        "ruta_macro": ruta_macro,
        "dist_dona_juana": dist_final_dj,
        "avenidas_dj": avenidas_dj,
        "coords_dona_juana": coords_dona_juana,
        "num_scc": num_scc,
        "resumen_grados": resumen_grados,
        "aristas_dup": aristas_dup,
        "secuencia_tramos": secuencia_tramos,
        "dist_total_m": dist_total_m,
        "dist_rep_m": dist_rep_m,
        "aristas_base": aristas_base,
        "nodos_desbalance": nodos_desbalance,
        "centro": [round(lat_0, 6), round(lon_0, 6)]
    }


# ==============================================================================
# 2. BARRA LATERAL CON FORMULARIO (EVITA RECARGAS MIENTRAS MUEVES EL SLIDER)
# ==============================================================================
st.sidebar.header("⚙️ Parámetros de Operación")

lista_localidades = [loc for loc in LOCALIDADES_BOGOTA.keys() if loc != "Relleno Doña Juana"]

with st.sidebar.form("form_control_bogota"):
    localidad_sel = st.selectbox("1. Localidad de Bogotá:", lista_localidades, index=12)
    radio_m = st.slider(
        "2. Radio operativo (metros):",
        min_value=350, max_value=1000, value=550, step=50,
        help="Para evitar bloqueos del servidor público en la nube, usa entre 350m y 850m."
    )
    submitted = st.form_submit_button("🚀 Calcular y Cargar Simulador", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Capas Geoespaciales")
tipo_mapa = st.sidebar.radio(
    "3. Mapa Base:",
    ["Satelital Híbrido (Esri World Imagery + Vías)", "OpenStreetMap Callejero"]
)
mostrar_nodos = st.sidebar.checkbox("Mostrar nodos desbalanceados (Fuentes/Sumideros)", value=True)
mostrar_macro = st.sidebar.checkbox("Mostrar Ruta Vial Real a Doña Juana", value=True)


# ==============================================================================
# 3. EJECUCIÓN SEGURA CON MANEJO DE ERRORES
# ==============================================================================
try:
    with st.spinner(f"Calculando circuito óptimo de {localidad_sel} ({radio_m} m) y trazado vial a Doña Juana..."):
        datos = calcular_modelo_completo(localidad_sel, radio_m)
except Exception as e:
    st.error(f"⚠️ {e}")
    st.info("💡 Sugerencia: Reduce el radio operativo a 500 m o vuelve a pulsar 'Calcular y Cargar Simulador'.")
    st.stop()

dist_total_km = datos["dist_total_m"] / 1000.0
dist_muerta_km = datos["dist_rep_m"] / 1000.0
dist_neta_km = dist_total_km - dist_muerta_km
eficiencia = (dist_neta_km / dist_total_km) * 100 if dist_total_km > 0 else 0.0
resumen_grados = datos["resumen_grados"]

# --- PANEL DE KPIs ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Localidad / Operador", localidad_sel, LOCALIDADES_BOGOTA[localidad_sel]["ase"])
col2.metric("Intersecciones | Vías", f"{resumen_grados['total_nodos']} | {resumen_grados['total_aristas']}", f"{datos['aristas_dup']} vías repetidas")
col3.metric("Recorrido Micro (DCPP)", f"{dist_total_km:.2f} km", f"{dist_muerta_km:.2f} km tránsito muerto")
col4.metric("Eficiencia Euleriana", f"{eficiencia:.1f}%", "Óptimo global garantizado")
col5.metric("Ruta Vial a Doña Juana", f"{datos['dist_dona_juana']} km", f"Vía {' ➔ '.join(datos['ruta_macro'])}")


# ==============================================================================
# 4. GENERADOR DEL SIMULADOR INTERACTIVO EN VIVO (LEAFLET + JS)
# ==============================================================================
def construir_html_simulador(datos_sim, loc_nombre, usar_satelital, ver_nodos, ver_macro):
    tramos_json = json.dumps(datos_sim["secuencia_tramos"])
    base_json = json.dumps(datos_sim["aristas_base"])
    nodos_json = json.dumps(datos_sim["nodos_desbalance"] if ver_nodos else [])
    macro_json = json.dumps(datos_sim["coords_dona_juana"] if ver_macro else [])
    centro_json = json.dumps(datos_sim["centro"])
    dj_coord = json.dumps([LOCALIDADES_BOGOTA["Relleno Doña Juana"]["lat"], LOCALIDADES_BOGOTA["Relleno Doña Juana"]["lon"]])
    modo_sat = "true" if usar_satelital else "false"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: #0b0f19; font-family: 'Segoe UI', Roboto, sans-serif; color: #f8fafc; }}
            #contenedor {{ position: relative; width: 100%; height: 650px; border-radius: 10px; overflow: hidden; border: 1px solid #1e293b; }}
            #mapa {{ width: 100%; height: 100%; }}
            .panel-sim {{
                position: absolute; top: 12px; left: 54px; z-index: 1000;
                background: rgba(15, 23, 42, 0.92); backdrop-filter: blur(8px);
                padding: 12px 16px; border-radius: 10px; border: 1px solid #334155;
                width: 340px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            }}
            .titulo-sim {{ font-size: 13px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; display: flex; justify-content: space-between; }}
            .controles {{ display: flex; gap: 6px; margin-bottom: 10px; }}
            .btn {{
                flex: 1; padding: 7px 10px; border: none; border-radius: 6px;
                font-weight: 600; font-size: 12px; cursor: pointer; transition: 0.15s;
            }}
            .btn-play {{ background: #10b981; color: #052e16; }}
            .btn-play:hover {{ background: #34d399; }}
            .btn-pause {{ background: #f59e0b; color: #451a03; }}
            .btn-reset {{ background: #334155; color: #f8fafc; }}
            .btn-dj {{ background: #f97316; color: #fff; margin-top: 6px; width: 100%; }}
            .fila-slider {{ display: flex; align-items: center; justify-content: space-between; font-size: 12px; margin-top: 6px; color: #cbd5e1; }}
            input[type=range] {{ width: 100%; accent-color: #38bdf8; cursor: pointer; }}
            .hud-inferior {{
                position: absolute; bottom: 16px; left: 54px; z-index: 1000;
                background: rgba(15, 23, 42, 0.92); backdrop-filter: blur(8px);
                padding: 10px 16px; border-radius: 10px; border: 1px solid #334155;
                display: flex; gap: 22px; align-items: center; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            }}
            .hud-item {{ display: flex; flex-direction: column; }}
            .hud-label {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; }}
            .hud-val {{ font-size: 14px; font-weight: 700; color: #f8fafc; }}
            .leyenda {{
                position: absolute; top: 12px; right: 12px; z-index: 1000;
                background: rgba(15, 23, 42, 0.9); padding: 10px 14px; border-radius: 8px;
                border: 1px solid #334155; font-size: 11px; line-height: 1.7;
            }}
            .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
            .camion-icono {{
                background: #10b981; border: 2px solid #ffffff; border-radius: 50%;
                width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
                font-size: 14px; box-shadow: 0 0 14px #10b981;
            }}
        </style>
    </head>
    <body>
    <div id="contenedor">
        <div id="mapa"></div>

        <!-- Panel de Simulación -->
        <div class="panel-sim">
            <div class="titulo-sim">
                <span>🚛 Simulador DCPP - {loc_nombre}</span>
                <span id="estado-sim" style="color:#10b981;">Listo</span>
            </div>
            <div class="controles">
                <button class="btn btn-play" onclick="iniciarSimulacion()">▶ Iniciar</button>
                <button class="btn btn-pause" onclick="pausarSimulacion()">⏸ Pausa</button>
                <button class="btn btn-reset" onclick="reiniciarSimulacion()">↺ Reset</button>
            </div>
            <div class="fila-slider">
                <span>Progreso del Recorrido:</span>
                <span id="lbl-progreso">0 / 0 tramos</span>
            </div>
            <input type="range" id="slider-paso" min="0" value="0" oninput="saltarAPaso(this.value)"/>
            <div class="fila-slider">
                <span>Velocidad de Simulación:</span>
                <span id="lbl-vel">5x</span>
            </div>
            <input type="range" id="slider-vel" min="1" max="25" value="5" oninput="cambiarVelocidad(this.value)"/>
            <button class="btn btn-dj" onclick="simularViajeDonaJuana()">🛣️ Simular Viaje por Calles a Doña Juana</button>
        </div>

        <!-- Leyenda -->
        <div class="leyenda">
            <div><span class="dot" style="background:#00f2fe;"></span>Recolección Primaria (1ª vez)</div>
            <div><span class="dot" style="background:#a855f7;"></span>Tramo Repetido (Eulerización)</div>
            <div><span class="dot" style="background:#f97316;"></span>Ruta Vial Real a Doña Juana</div>
            <div><span class="dot" style="background:#ff3b30;"></span>Nodo Fuente (b &lt; 0)</div>
            <div><span class="dot" style="background:#ffcc00;"></span>Nodo Sumidero (b &gt; 0)</div>
        </div>

        <!-- HUD Inferior en Tiempo Real -->
        <div class="hud-inferior">
            <div class="hud-item">
                <span class="hud-label">Vía Actual del Camión</span>
                <span class="hud-val" id="hud-calle" style="color:#38bdf8;">Base Operativa {loc_nombre}</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">Tipo de Tramo</span>
                <span class="hud-val" id="hud-tipo">Punto de Partida</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">Distancia Acumulada</span>
                <span class="hud-val" id="hud-km">0.00 km</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">Carga Recolectada</span>
                <span class="hud-val" id="hud-ton">0.00 Ton</span>
            </div>
        </div>
    </div>

    <script>
        const tramos = {tramos_json};
        const mallaBase = {base_json};
        const nodosDesbalance = {nodos_json};
        const rutaDonaJuana = {macro_json};
        const centro = {centro_json};
        const djCoord = {dj_coord};
        const usarSatelital = {modo_sat};

        const map = L.map('mapa', {{ center: centro, zoom: 15, preferCanvas: true }});

        if (usarSatelital) {{
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Esri World Imagery', maxZoom: 19
            }}).addTo(map);
            L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Esri Transportation', maxZoom: 19
            }}).addTo(map);
        }} else {{
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: 'OpenStreetMap', maxZoom: 19
            }}).addTo(map);
        }}

        // 1. Dibujar malla vial base
        mallaBase.forEach(coords => {{
            L.polyline(coords, {{ color: '#ffffff', weight: 2, opacity: 0.32 }}).addTo(map);
        }});

        // 2. Dibujar ruta completa tenue de guía al fondo
        tramos.forEach(t => {{
            L.polyline(t.coords, {{ color: '#00f2fe', weight: 2, opacity: 0.18 }}).addTo(map);
        }});

        // 3. Dibujar nodos desbalanceados
        nodosDesbalance.forEach(n => {{
            const color = n.b < 0 ? '#ff3b30' : '#ffcc00';
            const tipo = n.b < 0 ? 'Fuente (Exceso Entrada)' : 'Sumidero (Exceso Salida)';
            L.circleMarker([n.lat, n.lon], {{
                radius: 4, color: color, fillColor: color, fillOpacity: 0.9, weight: 1
            }}).bindPopup(`<b>Nodo ID:</b> ${{n.id}}<br><b>Tipo:</b> ${{tipo}}<br><b>Demanda b(v):</b> ${{n.b}}`).addTo(map);
        }});

        // 4. Dibujar Ruta Vial Real calle por calle hacia Doña Juana
        if (rutaDonaJuana.length > 1) {{
            L.polyline(rutaDonaJuana, {{
                color: '#f97316', weight: 4.5, opacity: 0.85, dashArray: '8, 6'
            }}).bindTooltip('Ruta Vial Real hacia Relleno Sanitario Doña Juana').addTo(map);

            L.marker(djCoord).bindPopup('<b>Relleno Sanitario Doña Juana</b><br>Disposición Final Distrital').addTo(map);
        }}

        // 5. Capas dinámicas del simulador
        const capaRecorrido = L.layerGroup().addTo(map);
        const iconoCamion = L.divIcon({{
            className: '',
            html: '<div class="camion-icono">🚛</div>',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        }});

        const marcadorCamion = L.marker(centro, {{ icon: iconoCamion, zIndexOffset: 2000 }}).addTo(map);

        let pasoActual = 0;
        let timer = null;
        let velocidad = 5;
        let distAcumuladaM = 0;
        let tonAcumuladas = 0;
        let enViajeDJ = false;
        let indiceDJ = 0;

        const sliderPaso = document.getElementById('slider-paso');
        sliderPaso.max = tramos.length;
        document.getElementById('lbl-progreso').innerText = `0 / ${{tramos.length}} tramos`;

        function dibujarHastaPaso(limite) {{
            capaRecorrido.clearLayers();
            distAcumuladaM = 0;
            tonAcumuladas = 0;

            for (let i = 0; i < limite; i++) {{
                const t = tramos[i];
                const colorTramo = t.repetida ? '#a855f7' : '#00f2fe';
                L.polyline(t.coords, {{
                    color: colorTramo,
                    weight: 5,
                    opacity: 0.95
                }}).addTo(capaRecorrido);

                distAcumuladaM += t.longitud_m;
                if (!t.repetida) {{
                    tonAcumuladas += (t.longitud_m / 1000.0) * 0.28;
                }}
            }}

            if (limite > 0) {{
                const ultimo = tramos[limite - 1];
                const coordFinal = ultimo.coords[ultimo.coords.length - 1];
                marcadorCamion.setLatLng(coordFinal);
                document.getElementById('hud-calle').innerText = ultimo.calle;
                document.getElementById('hud-tipo').innerText = ultimo.repetida ? '🔄 Tramo Repetido (Enlace)' : '🗑️ Recolección Activa';
                document.getElementById('hud-tipo').style.color = ultimo.repetida ? '#c084fc' : '#4ade80';
            }} else {{
                marcadorCamion.setLatLng(centro);
                document.getElementById('hud-calle').innerText = 'Base Operativa {loc_nombre}';
                document.getElementById('hud-tipo').innerText = 'Punto de Partida';
                document.getElementById('hud-tipo').style.color = '#f8fafc';
            }}

            document.getElementById('hud-km').innerText = (distAcumuladaM / 1000.0).toFixed(2) + ' km';
            document.getElementById('hud-ton').innerText = tonAcumuladas.toFixed(2) + ' Ton';
            document.getElementById('lbl-progreso').innerText = `${{limite}} / ${{tramos.length}} tramos`;
            sliderPaso.value = limite;
        }}

        function avanzarTick() {{
            if (enViajeDJ) {{
                if (indiceDJ < rutaDonaJuana.length) {{
                    const pt = rutaDonaJuana[indiceDJ];
                    marcadorCamion.setLatLng(pt);
                    if (indiceDJ > 0) {{
                        L.polyline([rutaDonaJuana[indiceDJ - 1], pt], {{
                            color: '#facc15', weight: 6, opacity: 1.0
                        }}).addTo(capaRecorrido);
                    }}
                    map.panTo(pt, {{ animate: true, duration: 0.1 }});
                    indiceDJ += Math.max(1, Math.floor(velocidad / 2));
                }} else {{
                    pausarSimulacion();
                    document.getElementById('estado-sim').innerText = 'En Doña Juana';
                    document.getElementById('hud-calle').innerText = 'Relleno Sanitario Doña Juana';
                    document.getElementById('hud-tipo').innerText = '✅ Descarga Finalizada';
                }}
                return;
            }}

            if (pasoActual < tramos.length) {{
                pasoActual++;
                dibujarHastaPaso(pasoActual);
            }} else {{
                pausarSimulacion();
                document.getElementById('estado-sim').innerText = 'Completado';
            }}
        }}

        function iniciarSimulacion() {{
            if (timer) clearInterval(timer);
            document.getElementById('estado-sim').innerText = enViajeDJ ? 'Viajando a DJ' : 'En Ruta';
            const intervaloMs = Math.max(15, Math.floor(220 / velocidad));
            timer = setInterval(avanzarTick, intervaloMs);
        }}

        function pausarSimulacion() {{
            if (timer) clearInterval(timer);
            timer = null;
            document.getElementById('estado-sim').innerText = 'Pausado';
        }}

        function reiniciarSimulacion() {{
            pausarSimulacion();
            enViajeDJ = false;
            pasoActual = 0;
            dibujarHastaPaso(0);
            map.setView(centro, 15);
            document.getElementById('estado-sim').innerText = 'Listo';
        }}

        function saltarAPaso(val) {{
            enViajeDJ = false;
            pasoActual = parseInt(val);
            dibujarHastaPaso(pasoActual);
        }}

        function cambiarVelocidad(val) {{
            velocidad = parseInt(val);
            document.getElementById('lbl-vel').innerText = velocidad + 'x';
            if (timer) iniciarSimulacion();
        }}

        function simularViajeDonaJuana() {{
            if (rutaDonaJuana.length < 2) return;
            pausarSimulacion();
            enViajeDJ = true;
            indiceDJ = 0;
            document.getElementById('hud-calle').innerText = 'Corredor Vial hacia Doña Juana';
            document.getElementById('hud-tipo').innerText = '🚛 Tránsito Arterial (Dijkstra + OSRM)';
            document.getElementById('hud-tipo').style.color = '#fb923c';
            map.fitBounds(L.polyline(rutaDonaJuana).getBounds(), {{ padding: [40, 40] }});
            iniciarSimulacion();
        }}
    </script>
    </body>
    </html>
    """


# --- PESTAÑAS PRINCIPALES ---
tab_mapa, tab_teoria, tab_tabla = st.tabs([
    "🛰️ Simulador Satelital en Vivo (Micro + Macro)",
    "📐 Demostración Matemática y Teoría Aplicada",
    "📋 Hoja de Ruta Paso a Paso (Hierholzer)"
])

with tab_mapa:
    usar_sat = "Satelital" in tipo_mapa
    html_simulador = construir_html_simulador(
        datos, localidad_sel, usar_sat, mostrar_nodos, mostrar_macro
    )
    components.html(html_simulador, height=660, scrolling=False)

    st.download_button(
        label="💾 Descargar Simulador Interactivo Completo como archivo HTML independiente",
        data=html_simulador,
        file_name=f"simulador_aseo_{localidad_sel.lower().replace(' ', '_')}.html",
        mime="text/html"
    )

with tab_teoria:
    st.subheader("Sustentación Matemática Calculada en Tiempo Real sobre el Grafo Actual")
    avenidas_texto = ", ".join(datos["avenidas_dj"]) if datos["avenidas_dj"] else "Corredores Arteriales Distritales"
    st.markdown(f"""
    #### 1. Filtrado Topológico por Conectividad Fuerte (Algoritmo de Tarjan)
    En la descarga bruta de **{localidad_sel}** se identificaron **{datos['num_scc']} componentes conexas**. 
    Para garantizar que el camión compactador siempre pueda regresar al punto de partida sin quedar atrapado en vías cerradas, se extrajo el subgrafo maximal $G_{{SCC}} = (V, E)$ con:
    * $|V| = {resumen_grados['total_nodos']}$ vértices (intersecciones viales).
    * $|E| = {resumen_grados['total_aristas']}$ aristas dirigidas (segmentos de vía con sentido).

    ---
    #### 2. Verificación del Teorema de Euler y Desbalance de Grados
    Para cada esquina $v \\in V$ se calculó el balance $\\text{{demanda}}(v) = \\text{{deg}}^+(v) - \\text{{deg}}^-(v)$:
    * **Nodos Balanceados ($\\text{{deg}}^+(v) = \\text{{deg}}^-(v)$):** `{resumen_grados['balanceados']}` intersecciones.
    * **Nodos Fuente ($\\text{{deg}}^-(v) > \\text{{deg}}^+(v)$):** `{resumen_grados['fuentes']}` intersecciones (puntos rojos).
    * **Nodos Sumidero ($\\text{{deg}}^+(v) > \\text{{deg}}^-(v)$):** `{resumen_grados['sumideros']}` intersecciones (puntos amarillos).

    ---
    #### 3. Eulerización por Flujo de Costo Mínimo (Network Simplex)
    Se resolvió el problema de optimización lineal:
    $$\\min \\sum_{{e \\in E}} w(e) \\cdot f(e) \\quad \\text{{sujeto a}} \\quad \\sum f(\\text{{entrantes}}) - \\sum f(\\text{{salientes}}) = \\text{{deg}}^+(v) - \\text{{deg}}^-(v)$$
    * **Resultado:** Se duplicaron exactamente **`{datos['aristas_dup']}` aristas** (`{dist_muerta_km:.2f} km` de tránsito de enlace), logrando que $\\text{{is\\_eulerian}}(G_{{euler}}) = \\text{{True}}$.

    ---
    #### 4. Ruta Vial Real hacia Relleno Doña Juana (Dijkstra + Geometría Vial OSRM)
    * **Secuencia de localidades (Dijkstra):** `{" ➔ ".join(datos['ruta_macro'])}`
    * **Principales corredores viales tomados calle por calle:** `{avenidas_texto}`
    * **Distancia real sobre malla vial:** `{datos['dist_dona_juana']} km`
    """)

with tab_tabla:
    st.subheader(f"Hoja de Ruta Secuencial Generada por tu Algoritmo de Hierholzer ({len(datos['secuencia_tramos'])} tramos)")
    df_mostrar = pd.DataFrame(datos["secuencia_tramos"]).drop(columns=["coords"], errors="ignore")
    st.dataframe(df_mostrar, use_container_width=True, height=450)
