import networkx as nx

from src.graph.clustering import build_analysis_result, cluster_graph


def test_cluster_graph_returns_labels_for_all_nodes() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge('a', 'b')
    graph.add_edge('c', 'd')
    layout = {
        'a': (0.0, 0.0),
        'b': (1.0, 0.0),
        'c': (10.0, 0.0),
        'd': (11.0, 0.0),
    }

    result = cluster_graph(graph, layout)

    assert result['method'] in {'louvain', 'greedy_modularity', 'wcc'}
    assert result['node_ids'] == ['a', 'b', 'c', 'd']
    assert len(result['labels']) == 4
    assert result['n_clusters'] >= 2
    assert len(result['cluster_centroids_2d']) == result['n_clusters']


def test_cluster_graph_uses_wcc_fallback_for_large_graph() -> None:
    graph = nx.path_graph(5, create_using=nx.MultiDiGraph)
    layout = {str(node): (float(node), 0.0) for node in graph.nodes()}

    result = cluster_graph(graph, layout, max_louvain_nodes=2)

    assert result['method'] == 'wcc'
    assert result['n_clusters'] == 1


def test_build_analysis_result_includes_node_scoring() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge('a', 'b')
    layout = {'a': (0.0, 0.0), 'b': (1.0, 0.0)}

    result = build_analysis_result(graph, layout, {'a': 0.8, 'b': 0.2})

    assert result['clustering']['node_ids'] == ['a', 'b']
    assert result['node_scoring']['method'] == 'alert_noisy_or'
    assert result['node_scoring']['scores'] == [0.8, 0.2]
