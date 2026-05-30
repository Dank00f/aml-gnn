# API And SSE Contract

Базовый URL локального backend:

```text
http://127.0.0.1:9090/api/v1
```

## Health

```http
GET /health
```

Ответ:

```json
{
  "status": "ok"
}
```

## Upload IBM CSV

```http
POST /upload/ibm
Content-Type: multipart/form-data
```

Form fields:

| Поле | Тип | Обязательно |
|---|---|---|
| `file` | CSV file | да |

Ожидаемые IBM-колонки:

- `Timestamp`
- `From Bank`
- `Account`
- `To Bank`
- `Account.1`
- `Amount Received`
- `Receiving Currency`
- `Amount Paid`
- `Payment Currency`
- `Payment Format`
- `Is Laundering`

Ответ:

```json
{
  "session_id": "uuid"
}
```

Ошибки:

- `400` для пустого файла;
- `422` для отсутствующих колонок, некорректного timestamp или amount.

Excel upload сейчас не поддерживается.

## Upload Mapped CSV

```http
POST /upload
Content-Type: multipart/form-data
```

Form fields:

| Поле | Тип | Обязательно |
|---|---|---|
| `file` | CSV file | да |
| `column_mapping` | JSON string | да |

Минимальный mapping:

```json
{
  "sender_id": "sender",
  "receiver_id": "receiver",
  "amount_paid": "amount",
  "timestamp": "timestamp"
}
```

Дополнительные поля:

```json
{
  "sender_bank": null,
  "receiver_bank": null,
  "amount_received": null,
  "payment_currency": null,
  "receiving_currency": null,
  "transaction_type": null,
  "device_id": null,
  "ip_address": null,
  "is_laundering": null
}
```

## Graph API

```http
GET /sessions/{session_id}/stats
GET /sessions/{session_id}/graph
GET /sessions/{session_id}/alerts
GET /sessions/{session_id}/filters
GET /sessions/{session_id}/subgraph?node_id={id}&k=2
```

### Stats

```json
{
  "node_count": 12,
  "edge_count": 10,
  "alert_count": 6,
  "max_risk_score": 0.998,
  "laundering_label_count": 3,
  "amount_sum": 100000,
  "time_min": 1704067200,
  "time_max": 1704241500
}
```

### Graph Payload

```json
{
  "nodes": [
    {
      "id": "1:A001",
      "type": "account",
      "label": "1:A001",
      "x": 12.3,
      "y": -4.5,
      "risk_score": 0.99,
      "alerts": ["cycle_0"],
      "attributes": {}
    }
  ],
  "edges": [
    {
      "id": "tx_0",
      "source": "1:A001",
      "target": "2:A002",
      "amount": 10000.0,
      "timestamp": 1704067200,
      "risk_score": 0.99,
      "alerts": ["cycle_0"],
      "attributes": {}
    }
  ]
}
```

## SSE Stream

```http
GET /stream/{session_id}
Accept: text/event-stream
```

Для неизвестной session endpoint возвращает `404`.

Фактические event types:

| Event | Data | Назначение |
|---|---|---|
| `started` | `{}` | начало stream |
| `parsed` | `{}` | вход уже обработан upload pipeline |
| `graph_built` | `{}` | graph уже построен |
| `graph_meta` | `{session_id,node_count,edge_count}` | размеры graph |
| `nodes_chunk` | `{nodes:[...]}` | batch узлов |
| `edges_chunk` | `{edges:[...]}` | batch рёбер |
| `layout_done` | `{}` | координаты доступны |
| `detectors_done` | `{}` | detectors завершены |
| `detector_result` | `{pattern_type,items}` | alerts конкретного detector group |
| `analysis_result` | `{clustering,node_scoring}` | clustering labels, cluster metadata and node scoring aligned to node order |
| `scoring_done` | `{}` | risk scores доступны |
| `completed` | `{}` | результат готов |
| `stream_done` | `{}` | stream можно закрыть |

`error` event в happy-path generator не испускается. Ошибка неизвестной session обрабатывается HTTP `404`.

## Alert Shape

Detector alert содержит:

```json
{
  "id": "cycle_0",
  "type": "cycle",
  "score": 0.97,
  "node_ids": ["1:A001", "2:A002"],
  "edge_ids": ["tx_0"],
  "metrics": {}
}
```

Клиент может использовать `type`, `score`, `node_ids`, `edge_ids` и `metrics` для подсветки и деталей.

## Analysis Result Shape

`analysis_result` содержит:

```json
{
  "clustering": {
    "method": "louvain",
    "labels": [0, 0, 1],
    "node_ids": ["1:A001", "2:A002", "3:A003"],
    "n_clusters": 2,
    "cluster_centroids_2d": [[0.1, 0.2], [0.8, -0.1]],
    "type_centroids": {
      "account": [0.2, 0.1]
    },
    "metadata": {
      "clustering_method": "louvain",
      "clustering_reason": "NetworkX Louvain communities"
    }
  },
  "node_scoring": {
    "method": "alert_noisy_or",
    "scores": [0.99, 0.82, 0.0],
    "metadata": {
      "meaning": "risk attention indicator, not a fraud proof"
    }
  }
}
```

Для больших графов backend использует `wcc` fallback вместо Louvain, чтобы не блокировать MVP pipeline.
