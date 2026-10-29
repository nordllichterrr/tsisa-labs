from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .domain import ComplexEvalConfig, Direction

logger = logging.getLogger(__name__)


@dataclass
class ComplexEvalResult:
    alternatives: list[str]
    criteria: list[str]
    normalized: np.ndarray
    v_expert_avg: np.ndarray
    r_spread: np.ndarray
    z_spread_weights: np.ndarray
    w_combined: np.ndarray
    weighted: np.ndarray
    totals: np.ndarray
    ranking: list[tuple[str, float]]


def normalize_matrix(
    raw: np.ndarray, directions: Sequence[Direction]
) -> np.ndarray:
    if raw.ndim != 2:
        raise ValueError(f"Матрица должна быть 2D, получено {raw.ndim}D")
    if raw.shape[1] != len(directions):
        raise ValueError(
            f"Число столбцов {raw.shape[1]} != число критериев {len(directions)}"
        )
    if np.any(~np.isfinite(raw)):
        raise ValueError("Матрица содержит NaN или inf")

    out = np.zeros_like(raw, dtype=float)
    for j, direction in enumerate(directions):
        col = raw[:, j].astype(float)
        if direction == Direction.MAX:
            mx = col.max()
            if mx <= 0:
                raise ValueError(f"Критерий {j}: max={mx}, нормировка невозможна")
            out[:, j] = col / mx
        elif direction == Direction.MIN:
            mn = col.min()
            if mn <= 0:
                raise ValueError(f"Критерий {j}: min={mn}, нормировка невозможна")
            out[:, j] = mn / col
        else:
            raise ValueError(f"Неизвестное направление: {direction}")
    return out


def compute_complex_evaluation(
    matrix: np.ndarray, config: ComplexEvalConfig
) -> ComplexEvalResult:
    config.validate()
    P_raw = np.asarray(matrix, dtype=float)
    n, m = P_raw.shape
    if m != len(config.criteria):
        raise ValueError(f"Матрица {n}x{m}, критериев {len(config.criteria)}")

    directions = [c.direction for c in config.criteria]
    P = normalize_matrix(P_raw, directions)
    logger.info("P (нормированные оценки) = %s", np.round(P, 4))

    V = np.mean([e.weights for e in config.experts], axis=0)
    logger.info("V (усреднённые веса экспертов) = %s", np.round(V, 4))

    R_i = P.max(axis=0) - P.min(axis=0)
    R = R_i.sum()
    if R <= 0:
        raise ValueError("Суммарный разброс = 0, все оценки одинаковы")
    Z = R_i / R
    logger.info("R_i (разброс по критериям) = %s", np.round(R_i, 4))
    logger.info("Z (веса по разбросу) = %s", np.round(Z, 4))

    W = config.alpha * V + (1 - config.alpha) * Z
    logger.info("W (обобщённые веса, alpha=%.2f) = %s", config.alpha, np.round(W, 4))

    weighted = P * W
    totals = weighted.sum(axis=1)

    ranking = sorted(
        zip(config.alternatives, totals.tolist()),
        key=lambda kv: kv[1],
        reverse=True,
    )

    return ComplexEvalResult(
        alternatives=list(config.alternatives),
        criteria=[c.code for c in config.criteria],
        normalized=P,
        v_expert_avg=V,
        r_spread=R_i,
        z_spread_weights=Z,
        w_combined=W,
        weighted=weighted,
        totals=totals,
        ranking=ranking,
    )


def sensitivity_analysis(
    matrix: np.ndarray,
    config: ComplexEvalConfig,
    alphas: Sequence[float] = (0.3, 0.5, 0.7),
) -> list[dict]:
    results = []
    for a in alphas:
        cfg = ComplexEvalConfig(
            criteria=config.criteria,
            experts=config.experts,
            alternatives=config.alternatives,
            alpha=a,
        )
        res = compute_complex_evaluation(matrix, cfg)
        results.append({
            "alpha": a,
            "winner": res.ranking[0][0],
            "ranking": res.ranking,
        })
    return results
