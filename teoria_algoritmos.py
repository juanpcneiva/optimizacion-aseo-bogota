"""
================================================================================
MÓDULO 1: FUNDAMENTOS DE TEORÍA DE GRAFOS Y ALGORITMOS DE OPTIMIZACIÓN VIAL
================================================================================
Proyecto: Optimización de Recolección de Residuos Sólidos en Bogotá D.C.
Modelo Matemático: Problema del Cartero Chino Dirigido (DCPP) y Rutas Macro

MARCO TEÓRICO INTEGRADO EN EL CÓDIGO:
--------------------------------------------------------------------------------
1. DEFINICIÓN FORMAL DEL GRAFO VIAL:
   Sea G = (V, E, w) un grafo dirigido y ponderado donde:
   - V: Conjunto de vértices que representan intersecciones viales o centroides zonales.
   - E: Conjunto de aristas dirigidas (u, v) que representan segmentos de calle
        con el sentido de circulación vehicular permitido en Bogotá.
   - w(e): Función de peso w: E -> R+ que asigna la longitud en metros a cada vía.

2. CONDICIÓN DE EULER Y CONECTIVIDAD FUERTE (TEOREMA DE EULER-HIERHOLZER):
   Un grafo dirigido G posee un circuito euleriano (un ciclo cerrado que recorre
   cada arista al menos una vez) si y solo si:
   a) G es fuertemente conexo: Para todo par (u, v) in V, existe un camino
      dirigido de u a v y de v a u (filtrado mediante el Algoritmo de Tarjan).
   b) G es simétrico en grados (balanceado):
      deg+(v) = deg-(v)   para todo v in V
      donde deg+(v) es el grado de salida y deg-(v) es el grado de entrada.

3. EULERIZACIÓN MEDIANTE FLUJO DE COSTO MÍNIMO (MIN-COST FLOW):
   Cuando deg+(v) != deg-(v), se define el desbalance o demanda b(v) como:
      b(v) = deg+(v) - deg-(v)
   - Si b(v) > 0: El nodo tiene exceso de salidas y requiere recibir aristas (Sumidero).
   - Si b(v) < 0: El nodo tiene exceso de entradas y requiere expulsar aristas (Fuente).
   - Si b(v) = 0: El nodo está balanceado (Nodo de transbordo).
================================================================================
"""

import networkx as nx
from collections import defaultdict


def extraer_componente_fuertemente_conexa(G_raw):
    """
    Aplica el Algoritmo de Tarjan (complejidad O(|V| + |E|)) para encontrar
    la Componente Fuertemente Conexa (SCC) maximal de la red vial.
    Garantiza que el camión recolector no quede atrapado en callejones cerrados.
    """
    componentes = list(nx.strongly_connected_components(G_raw))
    scc_maximal = max(componentes, key=len)
    G_scc = G_raw.subgraph(scc_maximal).copy()
    return G_scc, len(componentes)


def analizar_desbalance_grados(G):
    """
    Evalúa la condición de simetría deg+(v) = deg-(v) en cada intersección.
    Retorna el diccionario de demandas b(v) y las estadísticas de nodos.
    """
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    
    demandas = {}
    nodos_fuente = 0     # b(v) < 0: in > out (expulsan flujo adicional)
    nodos_sumidero = 0   # b(v) > 0: out > in (reciben flujo adicional)
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
    Resuelve el problema de programación lineal de Flujo de Costo Mínimo:
        min sum_{e in E} w(e) * f(e)
        sujeto a: sum_{v} f(v, u) - sum_{v} f(u, v) = b(u)
    Duplica las aristas óptimas para transformar G en un multigrafo euleriano.
    """
    red_flujo = nx.DiGraph()

    for v, b_v in demandas.items():
        red_flujo.add_node(v, demand=b_v)

    for u, v, data in G.edges(data=True):
        peso_metros = int(round(data.get("length", 1.0)))
        red_flujo.add_edge(u, v, weight=peso_metros, capacity=999)

    # Solución mediante Simplex de Redes (Network Simplex)
    flujo_optimo = nx.min_cost_flow(red_flujo)

    # Construcción del Multigrafo Dirigido Euleriano G_euler
    G_euler = nx.MultiDiGraph()
    for n, data in G.nodes(data=True):
        G_euler.add_node(n, **data)

    for u, v, data in G.edges(data=True):
        G_euler.add_edge(u, v, repetida=False, **data)

    aristas_duplicadas = 0
    for u in flujo_optimo:
        for v, unidades_flujo in flujo_optimo[u].items():
            if unidades_flujo > 0:
                datos_originales = list(G.get_edge_data(u, v).values())[0].copy()
                for _ in range(unidades_flujo):
                    G_euler.add_edge(u, v, repetida=True, **datos_originales)
                    aristas_duplicadas += 1

    return G_euler, aristas_duplicadas


def algoritmo_hierholzer_propio(G_euler, nodo_inicio=None):
    """
    IMPLEMENTACIÓN PROPIA DEL ALGORITMO DE HIERHOLZER (1873)
    ----------------------------------------------------------------------------
    Complejidad Temporal: O(|E_euler|)
    Extrae el circuito euleriano paso a paso usando dos estructuras:
    - Pila de exploración (stack): Mantiene el camino activo de búsqueda DFS.
    - Lista de circuito (circuito): Almacena los vértices cuando ya no tienen
      aristas salientes disponibles, invirtiendo el resultado al finalizar.
    """
    # Crear lista de adyacencia mutable con las aristas disponibles
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
            # Tomar la siguiente arista dirigida no visitada que sale de 'u'
            v, key, data = adyacencia[u].pop()
            stack.append(v)
        else:
            # Si 'u' ya no tiene aristas de salida sin visitar, se añade al circuito
            camino_nodos.append(stack.pop())

    # Invertir para obtener el sentido cronológico correcto del camión
    camino_nodos.reverse()

    # Reconstruir la secuencia de tramos (u, v, datos)
    # Usamos una copia de las aristas para calcular métricas exactas
    aristas_temp = defaultdict(list)
    for u, v, key, data in G_euler.edges(keys=True, data=True):
        aristas_temp[(u, v)].append(data)

    secuencia_tramos = []
    distancia_total = 0.0
    distancia_repetida = 0.0

    for i in range(len(camino_nodos) - 1):
        u = camino_nodos[i]
        v = camino_nodos[i + 1]
        datos_arista = aristas_temp[(u, v)].pop(0)
        longitud = datos_arista.get("length", 0.0)
        es_repetida = datos_arista.get("repetida", False)

        distancia_total += longitud
        if es_repetida:
            distancia_repetida += longitud

        secuencia_tramos.append({
            "paso": i + 1,
            "origen": u,
            "destino": v,
            "calle": datos_arista.get("name", "Vía Local"),
            "longitud_m": round(longitud, 1),
            "repetida": es_repetida
        })

    return secuencia_tramos, distancia_total, distancia_repetida


def dijkstra_macro_dona_juana(G_macro, localidad_origen):
    """
    Calcula la ruta más corta desde el centro de acopio de una localidad de Bogotá
    hasta el Relleno Sanitario Doña Juana usando el Algoritmo de Dijkstra O(|E| + |V| log |V|).
    """
    destino = "Relleno Doña Juana"
    ruta_nodos = nx.dijkstra_path(G_macro, source=localidad_origen, target=destino, weight="distancia_km")
    distancia_km = nx.dijkstra_path_length(G_macro, source=localidad_origen, target=destino, weight="distancia_km")
    return ruta_nodos, round(distancia_km, 2)