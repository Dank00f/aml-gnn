# 07. Clustering And Layout For Beginner

## Что такое clustering

Clustering группирует связанные узлы графа. Это помогает видеть области графа, которые структурно ближе друг к другу.

## Что такое layout

Layout рассчитывает координаты узлов на экране: `x` и `y`. Layout не ищет мошенничество, он помогает удобно показать граф.

## Где находится код

| Файл | Назначение |
|---|---|
| `backend/src/graph/clustering.py` | Louvain/WCC clustering |
| `backend/src/graph/layout.py` | Расчёт координат |
| `backend/tests/test_clustering.py` | Тесты clustering |
| `backend/tests/test_layout_payload.py` | Тесты layout payload |

## Что реализовано

- Louvain для небольших графов, если доступен в NetworkX.
- Greedy modularity fallback, если Louvain недоступен.
- WCC fallback для крупных графов, чтобы pipeline не блокировался.
- Layout через ForceAtlas2 при наличии NetworkX API и fallback на spring layout.

## Что такое AGC

AGC — отдельный алгоритм кластеризации. В текущем backend pipeline AGC не реализован и должен описываться только как roadmap.

## Как проверить

```powershell
cd backend
uv run pytest tests/test_clustering.py tests/test_layout_payload.py
```

## Что сказать на защите

«Кластеризация используется для визуальной группировки связанных областей графа. Раскладка отвечает за координаты узлов и не является AML-детектором. Для устойчивого MVP используется Louvain/WCC и layout fallback».
