# AML Graph

MVP РґРёРїР»РѕРјРЅРѕРіРѕ РїСЂРѕРµРєС‚Р° РґР»СЏ РІРёР·СѓР°Р»СЊРЅРѕРіРѕ AML/anti-fraud Р°РЅР°Р»РёР·Р° С‚СЂР°РЅР·Р°РєС†РёРѕРЅРЅРѕРіРѕ РіСЂР°С„Р°.

РўРµРєСѓС‰РёР№ РїСЂРѕРІРµСЂРµРЅРЅС‹Р№ СЃРѕСЃС‚Р°РІ:

- FastAPI backend;
- pandas parser РґР»СЏ IBM Transactions for AML CSV;
- NetworkX `MultiDiGraph`;
- rule-based detectors: cycles, fan-out, transit, shared device/IP;
- risk scoring РїРѕ alerts;
- clustering: Louvain РЅР° РЅРµР±РѕР»СЊС€РёС… РіСЂР°С„Р°С… Рё WCC fallback РЅР° РєСЂСѓРїРЅС‹С…;
- server-side layout;
- SSE stream;
- frontend РёР· Р°СЂС…РёРІРЅРѕР№ РІРµСЂСЃРёРё РїСЂРѕРµРєС‚Р° РЅР° Next.js + React + TypeScript + cosmos.gl;
- frontend risk filter, detail panel РІС‹Р±СЂР°РЅРЅРѕРіРѕ СѓР·Р»Р° Рё СЂР°СЃРєСЂС‹РІР°РµРјС‹Рµ РґРµС‚Р°Р»Рё СЃРІСЏР·Р°РЅРЅС‹С… С‚СЂР°РЅР·Р°РєС†РёР№;
- backend tests;
- benchmark script.
- optional offline GNN dataset and NumPy GCN baseline.

## РЎС‚РµРє

Backend:

- Python 3.14;
- FastAPI;
- pandas;
- NetworkX;
- Pydantic;
- SSE;
- in-memory session storage;
- pytest, ruff, ty.

Frontend:

- Next.js 16;
- React 19;
- TypeScript;
- Radix UI;
- Tailwind CSS;
- `@cosmos.gl/graph`.

РќРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ С‚РµРєСѓС‰РµРј backend runtime: PostgreSQL, Redis, RabbitMQ, Taskiq, LadybugDB, GNN training/inference.

## Р—Р°РїСѓСЃРє Backend

```powershell
cd D:\DESKTOP\aml-gnn\backend
uv sync
uv run python -m src.main
```

РџСЂРѕРІРµСЂРєР°:

```powershell
Invoke-RestMethod http://127.0.0.1:9090/api/v1/health
```

РћР¶РёРґР°РµРјС‹Р№ РѕС‚РІРµС‚:

```json
{"status":"ok"}
```

## Р—Р°РїСѓСЃРє Frontend

```powershell
cd D:\DESKTOP\aml-gnn\frontend
npm.cmd install
npm.cmd run dev
```

РћС‚РєСЂС‹С‚СЊ:

```text
http://127.0.0.1:3000
```

Frontend РѕР¶РёРґР°РµС‚ backend РЅР°:

```text
http://127.0.0.1:9090
```

Р­С‚Рѕ Р·Р°РґР°РЅРѕ РІ `.env.example` С‡РµСЂРµР· `NEXT_PUBLIC_API_BASE`.

## CSV Р¤РѕСЂРјР°С‚

РћСЃРЅРѕРІРЅРѕР№ endpoint:

```http
POST /api/v1/upload/ibm
```

РћР¶РёРґР°РµРјС‹Рµ IBM columns:

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

РќРѕСЂРјР°Р»РёР·Р°С†РёСЏ:

- `sender_id = From Bank + ":" + Account`;
- `receiver_id = To Bank + ":" + Account.1`;
- `amount = Amount Paid`;
- `Is Laundering` С…СЂР°РЅРёС‚СЃСЏ РєР°Рє label Рё РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ rule-based scoring.

Excel upload РЅРµ РІРєР»СЋС‡С‘РЅ. `.xlsx/.xls` СЃРµР№С‡Р°СЃ roadmap.

## API

РЎРј. [docs/API_AND_SSE_CONTRACT.md](docs/API_AND_SSE_CONTRACT.md).

РћСЃРЅРѕРІРЅС‹Рµ endpoints:

```text
POST /api/v1/upload/ibm
POST /api/v1/upload
GET  /api/v1/stream/{session_id}
GET  /api/v1/sessions/{session_id}/stats
GET  /api/v1/sessions/{session_id}/graph
GET  /api/v1/sessions/{session_id}/alerts
GET  /api/v1/sessions/{session_id}/filters
GET  /api/v1/sessions/{session_id}/subgraph?node_id=...&k=2
```

Frontend Р°РґР°РїС‚РёСЂРѕРІР°РЅ Рє СЌС‚РѕРјСѓ РєРѕРЅС‚СЂР°РєС‚Сѓ. РђСЂС…РёРІРЅС‹Р№ frontend РёР·РЅР°С‡Р°Р»СЊРЅРѕ РѕР¶РёРґР°Р» `/api/v1/graph/processing/...`, РЅРѕ СЃРµР№С‡Р°СЃ РєР»РёРµРЅС‚СЃРєРёРµ С„СѓРЅРєС†РёРё РїРµСЂРµРїРѕРґРєР»СЋС‡РµРЅС‹ РЅР° С‚РµРєСѓС‰РёРµ backend endpoints.

SSE С‚Р°РєР¶Рµ РѕС‚РґР°С‘С‚ `analysis_result` СЃ cluster labels Рё node scoring РґР»СЏ РІРєР»Р°РґРєРё РєР»Р°СЃС‚РµСЂРѕРІ РІРѕ frontend.

## РџСЂРѕРІРµСЂРєРё

Backend:

```powershell
cd backend
uv run pytest
uv run ruff check . --config=ruff.toml
uv run ty check
```

Frontend:

```powershell
cd frontend
npm.cmd run eslint-check
npm.cmd run prettier-check
npm.cmd run build
```

API E2E smoke:

```powershell
cd backend
uv run pytest tests/test_e2e_mvp.py
```

## Docker

Р’ СЂРµРїРѕР·РёС‚РѕСЂРёРё РµСЃС‚СЊ `Dockerfile` Рё `docker-compose.yaml` РґР»СЏ backend Рё frontend:

```powershell
copy .env.example .env
docker compose -f docker-compose.yaml --env-file .env config
docker compose -f docker-compose.yaml --env-file .env up --build
```

Р’ С‚РµРєСѓС‰РµРј РѕРєСЂСѓР¶РµРЅРёРё Docker CLI РЅРµ РЅР°Р№РґРµРЅ, РїРѕСЌС‚РѕРјСѓ Docker Compose РЅРµ Р±С‹Р» РїРѕРґС‚РІРµСЂР¶РґС‘РЅ Р·Р°РїСѓСЃРєРѕРј. PostgreSQL, Redis, RabbitMQ Рё worker РІ С‚РµРєСѓС‰РёР№ compose РЅРµ РІС…РѕРґСЏС‚.

## Optional GNN Dataset

GNN РЅРµ РїРѕРґРєР»СЋС‡С‘РЅ Рє runtime backend Рё РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ upload pipeline. РЎРµР№С‡Р°СЃ РµСЃС‚СЊ offline NumPy GCN baseline, РіРґРµ РєР°Р¶РґР°СЏ С‚СЂР°РЅР·Р°РєС†РёСЏ СЃС‚Р°РЅРѕРІРёС‚СЃСЏ node, Р° `Is Laundering` РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РєР°Рє transaction-level label. Р РµР·СѓР»СЊС‚Р°С‚С‹ С‚РµРєСѓС‰РµРіРѕ smoke-СЌРєСЃРїРµСЂРёРјРµРЅС‚Р° СЃРѕС…СЂР°РЅРµРЅС‹ РІ `results/gnn_metrics.json` Рё `results/GNN_EXPERIMENT_REPORT.md`; СЌС‚Рѕ РјР°Р»РµРЅСЊРєРёР№ synthetic fixture, РЅРµ production evidence.

РџСЂРѕРІРµСЂРёС‚СЊ РїРѕСЃС‚СЂРѕРµРЅРёРµ dataset:

```powershell
cd backend
.\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input tests/fixtures/ibm_aml_patterns.csv --describe-only
```

Р—Р°РїСѓСЃС‚РёС‚СЊ NumPy GCN smoke-РѕР±СѓС‡РµРЅРёРµ:

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.ml.gnn_baseline --input backend\tests\fixtures\ibm_aml_patterns.csv --expand-size 1000 --epochs 200 --hidden-dim 16 --metrics-output results\gnn_metrics.json --report-output results\GNN_EXPERIMENT_REPORT.md
```

GNN training РѕСЃС‚Р°С‘С‚СЃСЏ offline-СЌРєСЃРїРµСЂРёРјРµРЅС‚РѕРј Рё РЅРµ РІС…РѕРґРёС‚ РІ upload pipeline. РќР° С‚РµРєСѓС‰РµРј synthetic expansion feature-only baseline РїРѕРєР°Р·С‹РІР°РµС‚ С‚Рµ Р¶Рµ РјРµС‚СЂРёРєРё, РїРѕСЌС‚РѕРјСѓ РїСЂРµРёРјСѓС‰РµСЃС‚РІРѕ GNN РЅРµ РґРѕРєР°Р·Р°РЅРѕ.

## Benchmark

```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m src.benchmark --input backend\tests\fixtures\ibm_aml_patterns.csv --results-dir results --sizes 1000,5000,10000 --layout-max-nodes 500
```

Outputs:

- `results/benchmark_results.csv`;
- `results/BENCHMARK_REPORT.md`.

РўРµРєСѓС‰РёР№ СѓСЃРїРµС€РЅС‹Р№ benchmark РїРѕРґС‚РІРµСЂР¶РґС‘РЅ РЅР° 1 000, 5 000 Рё 10 000 transactions. 50 000 Рё 100 000 transactions РЅРµ РїСЂРѕРІРµСЂРµРЅС‹ Рё РЅРµ РґРѕР»Р¶РЅС‹ Р·Р°СЏРІР»СЏС‚СЊСЃСЏ Р±РµР· СЃРІРµР¶РµРіРѕ СЂРµР·СѓР»СЊС‚Р°С‚Р° РІ `results/`.

## РћРіСЂР°РЅРёС‡РµРЅРёСЏ

- Session storage РЅР°С…РѕРґРёС‚СЃСЏ РІ РїР°РјСЏС‚Рё.
- Session results С‚РµСЂСЏСЋС‚СЃСЏ РїСЂРё restart backend.
- РќРµС‚ С„РѕРЅРѕРІРѕР№ РѕС‡РµСЂРµРґРё Р·Р°РґР°С‡ РІ С‚РµРєСѓС‰РµРј backend runtime.
- РќРµС‚ persistent database РІ С‚РµРєСѓС‰РµРј backend runtime.
- РќРµС‚ AGC clustering РІ С‚РµРєСѓС‰РµРј backend pipeline.
- РќРµС‚ GNN scoring.
- Shared device/IP detector РїСѓСЃС‚ РґР»СЏ С‡РёСЃС‚РѕРіРѕ IBM CSV Р±РµР· С‚Р°РєРёС… РєРѕР»РѕРЅРѕРє.
- NetworkX Рё server-side layout РѕРіСЂР°РЅРёС‡РёРІР°СЋС‚ РјР°СЃС€С‚Р°Р±.

