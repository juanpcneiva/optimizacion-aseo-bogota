"""
================================================================================
MÓDULO 1: FUNDAMENTOS DE TEORÍA DE GRAFOS Y ALGORITMOS DE OPTIMIZACIÓN VIAL
================================================================================
Proyecto: Optimización de Recolección de Residuos Sólidos en Bogotá D.C.
Modelo Matemático: Problema del Cartero Chino Dirigido (DCPP) y Rutas Macro
================================================================================
"""

import networkx as nx
from collections import defaultdict


def extraer_componente_fuertemente_conexa(G_raw):
    """
    Aplica el Algoritmo de Tarjan O(|V| + |E|) para obtener la Componente
    Fuertemente Conexa (SCC) maximal y evitar callejones sin salida.
    """
    componentes = list(nx.strongly_connected_components(G_raw))
    scc_maximal = max(componentes, key=len)
    G_scc = G_raw.subgraph(scc_maximal).copy()
    return G_scc, len(componentes)


def analizar_desbalance_grados(G):
    """
    Evalúa la condición de simetría deg+(v) = deg-(v) en cada intersección.
    b(v) = deg+(v) - deg-(v)
    """
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    demandas = {}
    nodos_fuente = 0
    nodos_sumidero = 0
    nodos_balanceados = 0

    for v in G.nodes():
        b_v = out_deg[v] - in_deg[v]
        demandas[v] = b_v
        if b_v < 0:
            nodos_fuente += 1
        elif b_v > 0:
            nodos_sumidero += 1
        else:
            nodos_balanceados += 1

    resumen = {
        "total_nodos": G.number_of_nodes(),
        "total_aristas": G.number_of_edges(),
        "fuentes": nodos_fuente,
        "sumideros": nodos_sumidero,
        "balanceados": nodos_balanceados
    }
    return demandas, resumen


def eulerizar_grafo_min_cost_flow(G, demandas):
    """
    Resuelve el Flujo de Costo Mínimo (Network Simplex) para duplicar
    el conjunto óptimo de vías que equilibra todos los grados del grafo.
    """
    red_flujo = nx.DiGraph()

    for v, b_v in demandas.items():
        red_flujo.add_node(v, demand=b_v)

    for u, v, data in G.edges(data=True):
        peso_metros = max(1, int(round(data.get("length", 1.0))))
        if red_flujo.has_edge(u, v):
            if peso_metros < red_flujo[u][v]["weight"]:
                red_flujo[u][v]["weight"] = peso_metros
        else:
            red_flujo.add_edge(u, v, weight=peso_metros, capacity=999)

    flujo_optimo = nx.min_cost_flow(red_flujo)

    G_euler = nx.MultiDiGraph()
    for n, data in G.nodes(data=True):
        G_euler.add_node(n, **data)

    for u, v, data in G.edges(data=True):
        G_euler.add_edge(u, v, repetida=False, **data)

    aristas_duplicadas = 0
    for u in flujo_optimo:
        for v, unidades_flujo in flujo_optimo[u].items():
            if unidades_flujo > 0:
                aristas_uv = list(G.get_edge_data(u, v).values())
                datos_originales = min(aristas_uv, key=lambda d: d.get("length", 1.0)).copy()
                for _ in range(unidades_flujo):
                    G_euler.add_edge(u, v, repetida=True, **datos_originales)
                    aristas_duplicadas += 1

    return G_euler, aristas_duplicadas


def _obtener_nombre_via(valor_name):
    if isinstance(valor_name, list):
        return str(valor_name[0]) if valor_name else "Vía Local"
    if isinstance(valor_name, str) and valor_name.strip():
        return valor_name
    return "Vía Local"


def _extraer_coordenadas_arista(G, u, v, datos_arista):
    """
    Devuelve la lista de coordenadas [[lat, lon], ...] respetando la curvatura
    real de la calle en OpenStreetMap.
    """
    if "geometry" in datos_arista:
        coords = [[round(pt[1], 6), round(pt[0], 6)] for pt in datos_arista["geometry"].coords]
        return coords
    return [
        [round(G.nodes[u]["y"], 6), round(G.nodes[u]["x"], 6)],
        [round(G.nodes[v]["y"], 6), round(G.nodes[v]["x"], 6)]
    ]


def algoritmo_hierholzer_propio(G_euler, nodo_inicio=None):
    """
    IMPLEMENTACIÓN PROPIA DEL ALGORITMO DE HIERHOLZER O(|E_euler|)
    Extrae el circuito euleriano completo y adjunta la geometría vial de cada paso.
    """
    adyacencia = defaultdict(list)
    for u, v, key, data in G_euler.edges(keys=True, data=True):
        adyacencia[u].append((v, key, data))

    if nodo_inicio is None:
        nodo_inicio = next(iter(G_euler.nodes()))

    stack = [nodo_inicio]
    camino_nodos = []

    while stack:
        u = stack[-1]
        if adyacencia[u]:
            v, key, data = adyacencia[u].pop()
            stack.append(v)
        else:
            camino_nodos.append(stack.pop())

    camino_nodos.reverse()

    # Priorizar primero la pasada de recolección (repetida=False) y luego la repetida
    aristas_temp = defaultdict(list)
    for u, v, key, data in G_euler.edges(keys=True, data=True):
        aristas_temp[(u, v)].append(data)
    for par in aristas_temp:
        aristas_temp[par].sort(key=lambda d: d.get("repetida", False))

    secuencia_tramos = []
    distancia_total = 0.0
    distancia_repetida = 0.0

    for i in range(len(camino_nodos) - 1):
        u = camino_nodos[i]
        v = camino_nodos[i + 1]
        datos_arista = aristas_temp[(u, v)].pop(0)
        longitud = float(datos_arista.get("length", 0.0))
        es_repetida = bool(datos_arista.get("repetida", False))
        nombre_calle = _obtener_nombre_via(datos_arista.get("name"))
        coords_tramo = _extraer_coordenadas_arista(G_euler, u, v, datos_arista)

        distancia_total += longitud
        if es_repetida:
            distancia_repetida += longitud

        secuencia_tramos.append({
            "paso": i + 1,
            "origen": u,
            "destino": v,
            "calle": nombre_calle,
            "longitud_m": round(longitud, 1),
            "repetida": es_repetida,
            "coords": coords_tramo
        })

    return secuencia_tramos, distancia_total, distancia_repetida


def dijkstra_macro_dona_juana(G_macro, localidad_origen):
    """
    Calcula la secuencia óptima de corredores entre la localidad de origen
    y el Relleno Sanitario Doña Juana mediante el Algoritmo de Dijkstra.
    """
    destino = "Relleno Doña Juana"
    ruta_nodos = nx.dijkstra_path(G_macro, source=localidad_origen, target=destino, weight="distancia_km")
    distancia_km = nx.dijkstra_path_length(G_macro, source=localidad_origen, target=destino, weight="distancia_km")
    return ruta_nodos, round(distancia_km, 2)
