import time
from collections import defaultdict
from typing import Any, Literal

import networkx as nx

__all__ = ['build_analysis_result', 'cluster_graph']

ClusterMethod = Literal['louvain', 'greedy_modularity', 'wcc']
AnyGraph = nx.Graph | nx.DiGraph | nx.MultiGraph | nx.MultiDiGraph


def _undirected_simple_graph(graph: AnyGraph) -> nx.Graph:
    simple = nx.Graph()
    simple.add_nodes_from(graph.nodes())
    simple.add_edges_from((u, v) for u, v in graph.edges())
    return simple


def _communities(graph: nx.Graph, max_louvain_nodes: int) -> tuple[ClusterMethod, list[set], str]:
    if graph.number_of_nodes() == 0:
        return 'wcc', [], 'empty graph'

    if graph.number_of_nodes() > max_louvain_nodes:
        return (
            'wcc',
            [set(component) for component in nx.connected_components(graph)],
            f'graph has more than {max_louvain_nodes} nodes; using WCC fallback',
        )

    if hasattr(nx.community, 'louvain_communities'):
        return (
            'louvain',
            [set(c) for c in nx.community.louvain_communities(graph, seed=42)],
            'NetworkX Louvain communities',
        )

    return (
        'greedy_modularity',
        [set(c) for c in nx.community.greedy_modularity_communities(graph)],
        'NetworkX greedy modularity fallback',
    )


def _centroids(
    communities: list[set],
    node_ids: list[str],
    layout: dict[str, tuple[float, float]],
) -> list[tuple[float, float]]:
    centroids: list[tuple[float, float]] = []
    for community in communities:
        positions = [layout.get(str(node), (0.0, 0.0)) for node in community]
        if not positions:
            centroids.append((0.0, 0.0))
            continue
        centroids.append((
            sum(x for x, _ in positions) / len(positions),
            sum(y for _, y in positions) / len(positions),
        ))
    if centroids:
        return centroids
    return [layout.get(node_id, (0.0, 0.0)) for node_id in node_ids]


def _type_centroids(
    graph: AnyGraph,
    layout: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for node, attrs in graph.nodes(data=True):
        node_id = str(node)
        entity_type = str(attrs.get('entity_type', attrs.get('type', 'unknown')))
        grouped[entity_type].append(layout.get(node_id, (0.0, 0.0)))

    return {
        entity_type: (
            sum(x for x, _ in positions) / len(positions),
            sum(y for _, y in positions) / len(positions),
        )
        for entity_type, positions in grouped.items()
        if positions
    }


def cluster_graph(
    graph: AnyGraph,
    layout: dict[str, tuple[float, float]],
    max_louvain_nodes: int = 2000,
) -> dict[str, Any]:
    """Cluster graph nodes for frontend visualization."""
    started = time.perf_counter()
    simple = _undirected_simple_graph(graph)
    method, communities, reason = _communities(simple, max_louvain_nodes)

    communities = sorted(communities, key=lambda c: (-len(c), sorted(str(n) for n in c)[0]))
    node_to_cluster = {
        str(node): cluster_id
        for cluster_id, community in enumerate(communities)
        for node in community
    }

    node_ids = [str(node) for node in graph.nodes()]
    labels = [node_to_cluster.get(node_id, index) for index, node_id in enumerate(node_ids)]
    centroids = _centroids(communities, node_ids, layout)
    elapsed_ms = (time.perf_counter() - started) * 1000

    return {
        'method': method,
        'labels': labels,
        'node_ids': node_ids,
        'n_clusters': len(set(labels)),
        'cluster_centroids_2d': centroids,
        'type_centroids': _type_centroids(graph, layout),
        'metadata': {
            'n_nodes': graph.number_of_nodes(),
            'n_edges': graph.number_of_edges(),
            'density': float(nx.density(simple)) if simple.number_of_nodes() > 1 else 0.0,
            'is_directed': graph.is_directed(),
            'clustering_method': method,
            'clustering_reason': reason,
            'clustering_extra': {
                'max_louvain_nodes': max_louvain_nodes,
            },
            'scoring_weights': {
                'detector_alerts': 1.0,
                'betweenness': 0.0,
                'pagerank': 0.0,
                'flow_imbalance': 0.0,
            },
            'scoring_reason': 'Scores are provided by alert-based Noisy-OR risk scoring.',
            'betweenness_exact': False,
            'betweenness_k': 0,
            'step_timings': [
                {
                    'step': 'clustering',
                    'duration_ms': elapsed_ms,
                    'started_at': '',
                    'finished_at': '',
                },
            ],
            'total_duration_ms': elapsed_ms,
            'algorithm_versions': {
                'networkx': nx.__version__,
            },
        },
    }


def build_analysis_result(
    graph: AnyGraph,
    layout: dict[str, tuple[float, float]],
    node_scores: dict[str, float],
) -> dict[str, Any]:
    """Build frontend analysis_result payload."""
    node_ids = [str(node) for node in graph.nodes()]
    return {
        'clustering': cluster_graph(graph, layout),
        'node_scoring': {
            'method': 'alert_noisy_or',
            'scores': [float(node_scores.get(node_id, 0.0)) for node_id in node_ids],
            'metadata': {
                'node_ids': node_ids,
                'score_range': [0.0, 1.0],
                'meaning': 'risk attention indicator, not a fraud proof',
            },
        },
    }
