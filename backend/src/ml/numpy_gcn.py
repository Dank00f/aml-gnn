import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from src.ml.gnn_dataset import TransactionGraphDataset

__all__ = [
    'build_numpy_gcn_manifest',
    'NumpyGcnMetrics',
    'NumpyGcnModel',
    'PredictionMetrics',
    'fit_numpy_gcn',
    'load_numpy_gcn_model',
    'predict_numpy_gcn',
    'save_numpy_gcn_model',
    'train_numpy_gcn',
]


@dataclass(frozen=True)
class SparseAdjacency:
    rows: np.ndarray
    cols: np.ndarray
    weights: np.ndarray


@dataclass(frozen=True)
class NumpyGcnModel:
    """Persisted residual NumPy GCN model artifact for offline inference."""

    model: str
    feature_names: list[str]
    mean: np.ndarray
    std: np.ndarray
    w0: np.ndarray
    b0: np.ndarray
    w1: np.ndarray
    b1: np.ndarray
    decision_threshold: float
    time_window_seconds: int | None = None
    edge_mode: str = 'shared_account'
    split_mode: str = 'stratified'


@dataclass(frozen=True)
class NumpyGcnMetrics:
    """Training summary for the residual NumPy GCN experiment."""

    status: str
    model: str
    epochs: int
    seed: int
    transaction_nodes: int
    transaction_edges: int
    feature_count: int
    train_size: int
    validation_size: int
    test_size: int
    loss: float
    decision_threshold: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    pr_auc: float | None
    confusion_matrix: dict[str, int]
    default_threshold_metrics: dict[str, object]
    validation_metrics: dict[str, object]
    top_k_metrics: dict[str, object]
    class_balance: dict[str, int]
    baselines: dict[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable training metrics."""
        return asdict(self)


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    pr_auc: float | None
    confusion_matrix: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PredictionMetrics:
    """Offline inference output for a transaction-node dataset."""

    model: str
    decision_threshold: float
    transaction_nodes: int
    transaction_edges: int
    predicted_positive_count: int
    positive_scores: list[float]
    predictions: list[int]
    evaluation: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable prediction payload."""
        return asdict(self)


def fit_numpy_gcn(
    dataset: TransactionGraphDataset,
    *,
    epochs: int = 200,
    hidden_dim: int = 16,
    learning_rate: float = 0.05,
    weight_decay: float = 0.001,
    seed: int = 42,
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    class_weighting: str = 'balanced',
    decision_threshold: float | None = None,
    time_window_seconds: int | None = None,
    edge_mode: str = 'shared_account',
    split_mode: str = 'stratified',
) -> tuple[NumpyGcnModel, NumpyGcnMetrics]:
    """Train the residual NumPy GCN and return both model artifact and metrics."""
    if dataset.num_nodes == 0:
        raise ValueError('GNN dataset is empty')
    if len(set(dataset.labels)) < 2:
        raise ValueError('GNN training requires at least two label classes')
    if class_weighting not in {'none', 'balanced'}:
        raise ValueError('class_weighting must be "none" or "balanced"')
    if split_mode not in {'stratified', 'temporal', 'temporal_stratified'}:
        raise ValueError(
            'split_mode must be "stratified", "temporal", or "temporal_stratified"',
        )

    rng = np.random.default_rng(seed)
    raw_x = np.asarray(dataset.features, dtype=np.float64)
    y = np.asarray(dataset.labels, dtype=np.int64)
    if split_mode == 'temporal':
        train_idx, validation_idx, test_idx = _temporal_three_way_split(
            dataset.num_nodes,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
        )
    elif split_mode == 'temporal_stratified':
        train_idx, validation_idx, test_idx = _temporal_stratified_three_way_split(
            y,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
        )
    else:
        train_idx, validation_idx, test_idx = _stratified_three_way_split(
            y,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
            rng=rng,
        )
    x, mean, std = _standardize(raw_x, train_idx)
    adjacency = _normalized_adjacency(dataset.num_nodes, dataset.edge_index)
    class_weights = _class_weights(y[train_idx], mode=class_weighting)

    input_dim = x.shape[1]
    w0 = rng.normal(0.0, np.sqrt(2.0 / max(1, input_dim)), size=(input_dim, hidden_dim))
    b0 = np.zeros(hidden_dim, dtype=np.float64)
    output_dim = hidden_dim * 2
    w1 = rng.normal(0.0, np.sqrt(2.0 / max(1, output_dim)), size=(output_dim, 2))
    b1 = np.zeros(2, dtype=np.float64)

    x_agg = _aggregate(adjacency, x, dataset.num_nodes)
    train_one_hot = _one_hot(y[train_idx], classes=2)
    train_sample_weights = class_weights[y[train_idx]]
    train_weight_sum = float(np.sum(train_sample_weights))
    last_loss = 0.0

    for _ in range(max(1, epochs)):
        hidden_pre = x_agg @ w0 + b0
        hidden = np.maximum(hidden_pre, 0.0)
        hidden_agg = _aggregate(adjacency, hidden, dataset.num_nodes)
        hidden_output = np.concatenate([hidden, hidden_agg], axis=1)
        logits = hidden_output @ w1 + b1
        probabilities = _softmax(logits)

        train_probabilities = probabilities[train_idx]
        last_loss = _cross_entropy(
            train_probabilities,
            y[train_idx],
            sample_weights=train_sample_weights,
        )
        last_loss += 0.5 * weight_decay * (float(np.sum(w0 * w0)) + float(np.sum(w1 * w1)))

        dlogits = np.zeros_like(probabilities)
        dlogits[train_idx] = (
            (train_probabilities - train_one_hot)
            * train_sample_weights[:, None]
            / max(1e-12, train_weight_sum)
        )

        dw1 = hidden_output.T @ dlogits + weight_decay * w1
        db1 = dlogits.sum(axis=0)
        dhidden_output = dlogits @ w1.T
        dhidden_direct = dhidden_output[:, :hidden_dim]
        dhidden_agg = dhidden_output[:, hidden_dim:]
        dhidden = dhidden_direct + _aggregate(adjacency, dhidden_agg, dataset.num_nodes)
        dhidden_pre = dhidden * (hidden_pre > 0.0)
        dw0 = x_agg.T @ dhidden_pre + weight_decay * w0
        db0 = dhidden_pre.sum(axis=0)

        w0 -= learning_rate * dw0
        b0 -= learning_rate * db0
        w1 -= learning_rate * dw1
        b1 -= learning_rate * db1

    model = NumpyGcnModel(
        model='residual_numpy_two_layer_gcn',
        feature_names=list(dataset.feature_names),
        mean=mean,
        std=std,
        w0=w0,
        b0=b0,
        w1=w1,
        b1=b1,
        decision_threshold=0.5,
        time_window_seconds=time_window_seconds,
        edge_mode=edge_mode,
        split_mode=split_mode,
    )
    positive_scores = _predict_scores(model, dataset)
    tuned_threshold = (
        float(decision_threshold)
        if decision_threshold is not None
        else _best_threshold(y[validation_idx], positive_scores[validation_idx])
    )
    model = NumpyGcnModel(
        model=model.model,
        feature_names=model.feature_names,
        mean=model.mean,
        std=model.std,
        w0=model.w0,
        b0=model.b0,
        w1=model.w1,
        b1=model.b1,
        decision_threshold=tuned_threshold,
        time_window_seconds=time_window_seconds,
        edge_mode=edge_mode,
        split_mode=split_mode,
    )
    predictions = (positive_scores >= tuned_threshold).astype(np.int64)

    baselines = {
        'majority_class': _majority_baseline(y, train_idx, test_idx),
        'feature_logistic_regression': _train_feature_baseline(
            x,
            y,
            train_idx,
            validation_idx,
            test_idx,
            epochs=max(1, epochs),
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            class_weighting=class_weighting,
            rng=np.random.default_rng(seed + 1),
        ),
    }

    metrics = _metrics(
        y_true=y[test_idx],
        y_pred=predictions[test_idx],
        y_score=positive_scores[test_idx],
        validation_true=y[validation_idx],
        validation_score=positive_scores[validation_idx],
        all_labels=y,
        dataset=dataset,
        epochs=max(1, epochs),
        seed=seed,
        train_size=len(train_idx),
        validation_size=len(validation_idx),
        loss=last_loss,
        threshold=tuned_threshold,
        baselines=baselines,
    )
    return model, metrics


def train_numpy_gcn(
    dataset: TransactionGraphDataset,
    *,
    epochs: int = 200,
    hidden_dim: int = 16,
    learning_rate: float = 0.05,
    weight_decay: float = 0.001,
    seed: int = 42,
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    class_weighting: str = 'balanced',
    decision_threshold: float | None = None,
    time_window_seconds: int | None = None,
    edge_mode: str = 'shared_account',
    split_mode: str = 'stratified',
) -> NumpyGcnMetrics:
    """Train the residual NumPy GCN and return only experiment metrics."""
    _, metrics = fit_numpy_gcn(
        dataset,
        epochs=epochs,
        hidden_dim=hidden_dim,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        seed=seed,
        train_ratio=train_ratio,
        validation_ratio=validation_ratio,
        class_weighting=class_weighting,
        decision_threshold=decision_threshold,
        time_window_seconds=time_window_seconds,
        edge_mode=edge_mode,
        split_mode=split_mode,
    )
    return metrics


def predict_numpy_gcn(
    model: NumpyGcnModel,
    dataset: TransactionGraphDataset,
    *,
    decision_threshold: float | None = None,
) -> PredictionMetrics:
    """Run offline inference with a saved residual NumPy GCN model."""
    if dataset.feature_names != model.feature_names:
        raise ValueError('Dataset feature_names do not match saved model feature_names')

    positive_scores = _predict_scores(model, dataset)
    threshold = (
        model.decision_threshold
        if decision_threshold is None
        else float(decision_threshold)
    )
    predictions = (positive_scores >= threshold).astype(np.int64)

    evaluation: dict[str, object] | None = None
    labels = np.asarray(dataset.labels, dtype=np.int64)
    if len(set(labels.tolist())) >= 2:
        evaluation = _classification_metrics(
            y_true=labels,
            y_pred=predictions,
            y_score=positive_scores,
        ).to_dict()

    return PredictionMetrics(
        model=model.model,
        decision_threshold=threshold,
        transaction_nodes=dataset.num_nodes,
        transaction_edges=dataset.num_edges,
        predicted_positive_count=int(np.sum(predictions == 1)),
        positive_scores=positive_scores.tolist(),
        predictions=predictions.tolist(),
        evaluation=evaluation,
    )


def save_numpy_gcn_model(model: NumpyGcnModel, path: str | Path) -> None:
    """Persist a trained residual NumPy GCN artifact into a compressed NPZ file."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        'model': model.model,
        'feature_names': model.feature_names,
        'decision_threshold': model.decision_threshold,
        'time_window_seconds': model.time_window_seconds,
        'edge_mode': model.edge_mode,
        'split_mode': model.split_mode,
    }
    np.savez_compressed(
        output,
        metadata=np.array([json.dumps(metadata)], dtype=object),
        mean=model.mean,
        std=model.std,
        w0=model.w0,
        b0=model.b0,
        w1=model.w1,
        b1=model.b1,
    )


def load_numpy_gcn_model(path: str | Path) -> NumpyGcnModel:
    """Load a persisted residual NumPy GCN artifact from a compressed NPZ file."""
    archive_path = Path(path)
    with np.load(archive_path, allow_pickle=True) as archive:
        metadata = json.loads(str(archive['metadata'][0]))
        return NumpyGcnModel(
            model=str(metadata['model']),
            feature_names=[str(value) for value in metadata['feature_names']],
            mean=np.asarray(archive['mean'], dtype=np.float64),
            std=np.asarray(archive['std'], dtype=np.float64),
            w0=np.asarray(archive['w0'], dtype=np.float64),
            b0=np.asarray(archive['b0'], dtype=np.float64),
            w1=np.asarray(archive['w1'], dtype=np.float64),
            b1=np.asarray(archive['b1'], dtype=np.float64),
            decision_threshold=float(metadata['decision_threshold']),
            time_window_seconds=(
                int(metadata['time_window_seconds'])
                if metadata.get('time_window_seconds') is not None
                else None
            ),
            edge_mode=str(metadata.get('edge_mode', 'shared_account')),
            split_mode=str(metadata.get('split_mode', 'stratified')),
        )


def build_numpy_gcn_manifest(
    model: NumpyGcnModel,
    *,
    metrics: NumpyGcnMetrics | None = None,
    input_path: str | None = None,
    input_format: str | None = None,
    sample_size: int | None = None,
    edge_mode: str | None = None,
    split_mode: str | None = None,
) -> dict[str, object]:
    """Build a JSON-serializable manifest for a persisted GNN artifact."""
    payload: dict[str, object] = {
        'model': model.model,
        'feature_names': model.feature_names,
        'feature_count': len(model.feature_names),
        'decision_threshold': model.decision_threshold,
        'time_window_seconds': model.time_window_seconds,
        'edge_mode': model.edge_mode,
        'split_mode': model.split_mode,
    }
    if input_path is not None:
        payload['input'] = input_path
    if input_format is not None:
        payload['input_format'] = input_format
    if sample_size is not None:
        payload['sample_size'] = sample_size
    if edge_mode is not None:
        payload['edge_mode'] = edge_mode
    if split_mode is not None:
        payload['split_mode'] = split_mode
    if metrics is not None:
        payload['training'] = {
            'epochs': metrics.epochs,
            'seed': metrics.seed,
            'train_size': metrics.train_size,
            'validation_size': metrics.validation_size,
            'test_size': metrics.test_size,
            'loss': metrics.loss,
            'accuracy': metrics.accuracy,
            'precision': metrics.precision,
            'recall': metrics.recall,
            'f1': metrics.f1,
            'roc_auc': metrics.roc_auc,
            'pr_auc': metrics.pr_auc,
        }
    return payload


def _predict_scores(model: NumpyGcnModel, dataset: TransactionGraphDataset) -> np.ndarray:
    x = np.asarray(dataset.features, dtype=np.float64)
    x = _apply_standardization(x, model.mean, model.std)
    adjacency = _normalized_adjacency(dataset.num_nodes, dataset.edge_index)
    x_agg = _aggregate(adjacency, x, dataset.num_nodes)
    hidden = np.maximum(x_agg @ model.w0 + model.b0, 0.0)
    hidden_agg = _aggregate(adjacency, hidden, dataset.num_nodes)
    hidden_output = np.concatenate([hidden, hidden_agg], axis=1)
    probabilities = _softmax(hidden_output @ model.w1 + model.b1)
    return probabilities[:, 1]


def _standardize(
    features: np.ndarray,
    train_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = features[train_idx].mean(axis=0)
    std = features[train_idx].std(axis=0)
    std = np.where(std == 0.0, 1.0, std)
    return _apply_standardization(features, mean, std), mean, std


def _apply_standardization(features: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (features - mean) / std


def _normalized_adjacency(num_nodes: int, edges: list[tuple[int, int]]) -> SparseAdjacency:
    pairs = {(index, index) for index in range(num_nodes)}
    for source, target in edges:
        pairs.add((source, target))
        pairs.add((target, source))

    rows = np.fromiter((row for row, _ in pairs), dtype=np.int64)
    cols = np.fromiter((col for _, col in pairs), dtype=np.int64)
    degree = np.bincount(rows, minlength=num_nodes).astype(np.float64)
    inv_sqrt_degree = np.zeros_like(degree)
    np.divide(1.0, np.sqrt(degree), out=inv_sqrt_degree, where=degree > 0)
    weights = inv_sqrt_degree[rows] * inv_sqrt_degree[cols]
    return SparseAdjacency(rows=rows, cols=cols, weights=weights)


def _aggregate(adjacency: SparseAdjacency, values: np.ndarray, num_nodes: int) -> np.ndarray:
    output = np.zeros((num_nodes, values.shape[1]), dtype=np.float64)
    weighted_values = values[adjacency.cols] * adjacency.weights[:, None]
    np.add.at(output, adjacency.rows, weighted_values)
    return output


def _stratified_three_way_split(
    labels: np.ndarray,
    *,
    train_ratio: float,
    validation_ratio: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if train_ratio <= 0.0 or validation_ratio < 0.0 or train_ratio + validation_ratio >= 1.0:
        raise ValueError('train_ratio and validation_ratio must leave a non-empty test split')

    train: list[int] = []
    validation: list[int] = []
    test: list[int] = []

    for label in sorted({int(v) for v in labels.tolist()}):
        indices = np.where(labels == label)[0]
        rng.shuffle(indices)
        if len(indices) < 3:
            train.extend(indices.tolist())
            continue

        train_count = int(round(len(indices) * train_ratio))
        validation_count = int(round(len(indices) * validation_ratio))
        train_count = min(max(1, train_count), len(indices) - 2)
        validation_count = min(max(1, validation_count), len(indices) - train_count - 1)

        train.extend(indices[:train_count].tolist())
        validation.extend(indices[train_count:train_count + validation_count].tolist())
        test.extend(indices[train_count + validation_count:].tolist())

    if not validation:
        validation = train.copy()
    if not test:
        test = validation.copy()

    rng.shuffle(train)
    rng.shuffle(validation)
    rng.shuffle(test)
    return (
        np.asarray(train, dtype=np.int64),
        np.asarray(validation, dtype=np.int64),
        np.asarray(test, dtype=np.int64),
    )


def _temporal_three_way_split(
    num_nodes: int,
    *,
    train_ratio: float,
    validation_ratio: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if train_ratio <= 0.0 or validation_ratio < 0.0 or train_ratio + validation_ratio >= 1.0:
        raise ValueError('train_ratio and validation_ratio must leave a non-empty test split')
    if num_nodes < 3:
        raise ValueError('temporal split requires at least three transaction nodes')

    train_end = max(1, int(round(num_nodes * train_ratio)))
    validation_end = max(train_end + 1, int(round(num_nodes * (train_ratio + validation_ratio))))
    validation_end = min(validation_end, num_nodes - 1)
    train_end = min(train_end, validation_end - 1)

    train_idx = np.arange(0, train_end, dtype=np.int64)
    validation_idx = np.arange(train_end, validation_end, dtype=np.int64)
    test_idx = np.arange(validation_end, num_nodes, dtype=np.int64)

    if len(validation_idx) == 0:
        validation_idx = test_idx.copy()
    if len(test_idx) == 0:
        test_idx = validation_idx.copy()
    return train_idx, validation_idx, test_idx


def _temporal_stratified_three_way_split(
    labels: np.ndarray,
    *,
    train_ratio: float,
    validation_ratio: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_parts: list[np.ndarray] = []
    validation_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    for label in (0, 1):
        indices = np.flatnonzero(labels == label)
        if len(indices) == 0:
            continue
        train_idx, validation_idx, test_idx = _temporal_three_way_split(
            len(indices),
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
        )
        train_parts.append(indices[train_idx])
        validation_parts.append(indices[validation_idx])
        test_parts.append(indices[test_idx])
    return (
        np.sort(np.concatenate(train_parts)),
        np.sort(np.concatenate(validation_parts)),
        np.sort(np.concatenate(test_parts)),
    )


def _class_weights(labels: np.ndarray, *, mode: str) -> np.ndarray:
    if mode == 'none':
        return np.ones(2, dtype=np.float64)

    counts = np.bincount(labels, minlength=2).astype(np.float64)
    total = float(np.sum(counts))
    weights = np.ones(2, dtype=np.float64)
    nonzero = counts > 0
    weights[nonzero] = total / (2.0 * counts[nonzero])
    return weights


def _one_hot(labels: np.ndarray, *, classes: int) -> np.ndarray:
    encoded = np.zeros((len(labels), classes), dtype=np.float64)
    encoded[np.arange(len(labels)), labels] = 1.0
    return encoded


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def _cross_entropy(
    probabilities: np.ndarray,
    labels: np.ndarray,
    *,
    sample_weights: np.ndarray,
) -> float:
    clipped = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
    return float(-np.sum(sample_weights * np.log(clipped)) / max(1e-12, np.sum(sample_weights)))


def _train_feature_baseline(
    x: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    class_weighting: str,
    rng: np.random.Generator,
) -> dict[str, object]:
    weights = rng.normal(0.0, np.sqrt(2.0 / max(1, x.shape[1])), size=(x.shape[1], 2))
    bias = np.zeros(2, dtype=np.float64)
    train_one_hot = _one_hot(y[train_idx], classes=2)
    class_weights = _class_weights(y[train_idx], mode=class_weighting)
    train_sample_weights = class_weights[y[train_idx]]
    train_weight_sum = float(np.sum(train_sample_weights))
    last_loss = 0.0

    for _ in range(epochs):
        logits = x @ weights + bias
        probabilities = _softmax(logits)
        train_probabilities = probabilities[train_idx]
        last_loss = _cross_entropy(
            train_probabilities,
            y[train_idx],
            sample_weights=train_sample_weights,
        )
        last_loss += 0.5 * weight_decay * float(np.sum(weights * weights))

        dlogits = np.zeros_like(probabilities)
        dlogits[train_idx] = (
            (train_probabilities - train_one_hot)
            * train_sample_weights[:, None]
            / max(1e-12, train_weight_sum)
        )
        weights -= learning_rate * (x.T @ dlogits + weight_decay * weights)
        bias -= learning_rate * dlogits.sum(axis=0)

    final_probabilities = _softmax(x @ weights + bias)
    scores = final_probabilities[:, 1]
    threshold = _best_threshold(y[validation_idx], scores[validation_idx])
    predictions = (scores >= threshold).astype(np.int64)
    metrics = _classification_metrics(
        y_true=y[test_idx],
        y_pred=predictions[test_idx],
        y_score=scores[test_idx],
    )
    payload = metrics.to_dict()
    payload['loss'] = float(last_loss)
    payload['decision_threshold'] = float(threshold)
    payload['default_threshold_metrics'] = _classification_metrics(
        y_true=y[test_idx],
        y_pred=(scores[test_idx] >= 0.5).astype(np.int64),
        y_score=scores[test_idx],
    ).to_dict()
    return payload


def _majority_baseline(
    y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> dict[str, object]:
    train_labels = y[train_idx]
    positive_count = int(np.sum(train_labels == 1))
    negative_count = int(np.sum(train_labels == 0))
    majority_label = 1 if positive_count > negative_count else 0
    predictions = np.full(len(test_idx), majority_label, dtype=np.int64)
    scores = np.full(len(test_idx), float(majority_label), dtype=np.float64)
    payload = _classification_metrics(
        y_true=y[test_idx],
        y_pred=predictions,
        y_score=scores,
    ).to_dict()
    payload['predicted_class'] = majority_label
    return payload


def _metrics(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray,
    validation_true: np.ndarray,
    validation_score: np.ndarray,
    all_labels: np.ndarray,
    dataset: TransactionGraphDataset,
    epochs: int,
    seed: int,
    train_size: int,
    validation_size: int,
    loss: float,
    threshold: float,
    baselines: dict[str, dict[str, object]],
) -> NumpyGcnMetrics:
    metrics = _classification_metrics(y_true=y_true, y_pred=y_pred, y_score=y_score)

    return NumpyGcnMetrics(
        status='trained',
        model='residual_numpy_two_layer_gcn',
        epochs=epochs,
        seed=seed,
        transaction_nodes=dataset.num_nodes,
        transaction_edges=dataset.num_edges,
        feature_count=len(dataset.feature_names),
        train_size=train_size,
        validation_size=validation_size,
        test_size=len(y_true),
        loss=float(loss),
        decision_threshold=float(threshold),
        accuracy=metrics.accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        roc_auc=metrics.roc_auc,
        pr_auc=metrics.pr_auc,
        confusion_matrix=metrics.confusion_matrix,
        default_threshold_metrics=_classification_metrics(
            y_true=y_true,
            y_pred=(y_score >= 0.5).astype(np.int64),
            y_score=y_score,
        ).to_dict(),
        validation_metrics=_classification_metrics(
            y_true=validation_true,
            y_pred=(validation_score >= threshold).astype(np.int64),
            y_score=validation_score,
        ).to_dict(),
        top_k_metrics=_top_k_metrics(y_true, y_score),
        class_balance=_class_balance(all_labels),
        baselines=baselines,
    )


def _classification_metrics(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray,
) -> ClassificationMetrics:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    total = max(1, len(y_true))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return ClassificationMetrics(
        accuracy=(tp + tn) / total,
        precision=precision,
        recall=recall,
        f1=f1,
        roc_auc=_roc_auc(y_true, y_score),
        pr_auc=_pr_auc(y_true, y_score),
        confusion_matrix={
            'tp': tp,
            'tn': tn,
            'fp': fp,
            'fn': fn,
        },
    )


def _class_balance(labels: np.ndarray) -> dict[str, int]:
    return {
        'negative': int(np.sum(labels == 0)),
        'positive': int(np.sum(labels == 1)),
    }


def _best_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    candidates = np.unique(np.concatenate([y_score, np.asarray([0.5])]))
    best_threshold = 0.5
    best_f1 = -1.0
    best_recall = -1.0

    for threshold in candidates:
        predictions = (y_score >= threshold).astype(np.int64)
        metrics = _classification_metrics(y_true=y_true, y_pred=predictions, y_score=y_score)
        if metrics.f1 > best_f1 or (metrics.f1 == best_f1 and metrics.recall > best_recall):
            best_f1 = metrics.f1
            best_recall = metrics.recall
            best_threshold = float(threshold)

    return best_threshold


def _top_k_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, object]:
    positives = int(np.sum(y_true == 1))
    values: dict[str, object] = {'positive_count': positives}
    if positives == 0:
        return values

    for k in [10, 50, 100, positives]:
        clipped_k = min(k, len(y_true))
        if clipped_k <= 0:
            continue
        top_indices = np.argsort(-y_score)[:clipped_k]
        true_positives = int(np.sum(y_true[top_indices] == 1))
        key = f'at_{k}' if k != positives else 'at_positive_count'
        values[key] = {
            'k': clipped_k,
            'precision': true_positives / clipped_k,
            'recall': true_positives / positives,
            'true_positives': true_positives,
        }
    return values


def _roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    positives = int(np.sum(y_true == 1))
    negatives = int(np.sum(y_true == 0))
    if positives == 0 or negatives == 0:
        return None

    order = np.argsort(-y_score)
    sorted_true = y_true[order]
    tps = np.cumsum(sorted_true == 1)
    fps = np.cumsum(sorted_true == 0)
    tpr = np.concatenate([[0.0], tps / positives, [1.0]])
    fpr = np.concatenate([[0.0], fps / negatives, [1.0]])
    return float(np.trapezoid(tpr, fpr))


def _pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    positives = int(np.sum(y_true == 1))
    if positives == 0:
        return None

    order = np.argsort(-y_score)
    sorted_true = y_true[order]
    tps = np.cumsum(sorted_true == 1)
    fps = np.cumsum(sorted_true == 0)
    recall = tps / positives
    precision = tps / np.maximum(1, tps + fps)
    recall = np.concatenate([[0.0], recall])
    precision = np.concatenate([[1.0], precision])
    return float(np.trapezoid(precision, recall))
