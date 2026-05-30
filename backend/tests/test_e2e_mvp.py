from pathlib import Path

from httpx import AsyncClient


FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'ibm_aml_patterns.csv'


async def test_mvp_ibm_upload_api_and_stream_flow(client: AsyncClient) -> None:
    upload = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm_aml_patterns.csv', FIXTURE_PATH.read_bytes(), 'text/csv')},
    )

    assert upload.status_code == 200
    session_id = upload.json()['session_id']

    stats = await client.get(f'/api/v1/sessions/{session_id}/stats')
    graph = await client.get(f'/api/v1/sessions/{session_id}/graph')
    alerts = await client.get(f'/api/v1/sessions/{session_id}/alerts')
    filters = await client.get(f'/api/v1/sessions/{session_id}/filters')
    subgraph = await client.get(f'/api/v1/sessions/{session_id}/subgraph?node_id=1:A001&k=1')
    stream = await client.get(f'/api/v1/stream/{session_id}')

    assert stats.status_code == 200
    stats_json = stats.json()
    assert stats_json['node_count'] == 12
    assert stats_json['edge_count'] == 10
    assert stats_json['laundering_label_count'] == 3
    assert stats_json['alert_count'] >= 3

    assert graph.status_code == 200
    graph_json = graph.json()
    assert len(graph_json['nodes']) == 12
    assert len(graph_json['edges']) == 10
    assert {node['id'] for node in graph_json['nodes']} >= {'1:A001', '2:A002', '3:A003'}
    assert all(isinstance(node['x'], int | float) for node in graph_json['nodes'])
    assert all(isinstance(node['y'], int | float) for node in graph_json['nodes'])

    assert alerts.status_code == 200
    alert_types = {alert['type'] for alert in alerts.json()['alerts']}
    assert {'cycle', 'fanout', 'transit'} <= alert_types

    assert filters.status_code == 200
    assert set(filters.json()['payment_formats']) == {'ACH', 'Cash', 'Wire'}

    assert subgraph.status_code == 200
    assert {node['id'] for node in subgraph.json()['nodes']} >= {'1:A001', '2:A002', '3:A003'}

    assert stream.status_code == 200
    stream_text = stream.text
    for event_name in [
        'event: graph_meta',
        'event: nodes_chunk',
        'event: edges_chunk',
        'event: detector_result',
        'event: analysis_result',
        'event: completed',
        'event: stream_done',
    ]:
        assert event_name in stream_text
