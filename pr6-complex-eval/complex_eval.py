from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Sequence

import numpy as np

logger = logging.getLogger("complex_eval")


@dataclass(frozen=True)
class Criterion:
    code: str
    name: str
    direction: str
    vark_axis: str | None = None


@dataclass(frozen=True)
class ExpertWeights:
    name: str
    weights: tuple[float, ...]


@dataclass
class ComplexEvalConfig:
    criteria: list[Criterion]
    experts: list[ExpertWeights]
    alternatives: list[str] = field(default_factory=list)

    def validate(self) -> None:
        m = len(self.criteria)
        if m == 0:
            raise ValueError("Должен быть хотя бы один критерий.")
        for e in self.experts:
            if len(e.weights) != m:
                raise ValueError(
                    f"Эксперт '{e.name}': {len(e.weights)} весов, ожидалось {m}."
                )
            if not np.isclose(sum(e.weights), 1.0, atol=1e-6):
                raise ValueError(
                    f"Эксперт '{e.name}': сумма весов = {sum(e.weights)}, ожидалось 1.0."
                )


@dataclass
class ComplexEvalResult:
    alternatives: list[str]
    criteria: list[str]
    raw_matrix: np.ndarray
    v_expert_avg: np.ndarray
    r_spread: np.ndarray
    z_spread_weights: np.ndarray
    w_combined: np.ndarray
    weighted_matrix: np.ndarray
    totals: np.ndarray
    ranking: list[tuple[str, float]]


def normalize_matrix(raw: np.ndarray, directions: Sequence[str]) -> np.ndarray:
    if raw.ndim != 2:
        raise ValueError("Матрица оценок должна быть двумерной.")
    if raw.shape[1] != len(directions):
        raise ValueError("Число столбцов матрицы не совпадает с числом критериев.")

    out = np.zeros_like(raw, dtype=float)
    for j, direction in enumerate(directions):
        col = raw[:, j].astype(float)
        if direction == "max":
            mx = col.max()
            out[:, j] = col / mx if mx > 0 else col
        elif direction == "min":
            mn = col.min()
            out[:, j] = mn / col if mn > 0 else col
        else:
            raise ValueError(f"Неизвестное направление критерия: {direction}")
    return out


def compute_complex_evaluation(
    matrix: np.ndarray,
    config: ComplexEvalConfig,
) -> ComplexEvalResult:
    config.validate()
    P = np.asarray(matrix, dtype=float)
    n, m = P.shape
    if m != len(config.criteria):
        raise ValueError(f"Матрица {n}x{m}, критериев {len(config.criteria)}.")

    V = np.mean([e.weights for e in config.experts], axis=0)
    logger.info("V (усреднённые веса экспертов) = %s", np.round(V, 4))

    R_i = P.max(axis=0) - P.min(axis=0)
    R = R_i.sum()
    if R <= 0:
        raise ValueError("Все критерии одинаковы у всех альтернатив — разброс = 0.")
    logger.info("R_i (разброс по критериям) = %s", np.round(R_i, 4))
    logger.info("R (суммарный разброс) = %.4f", R)

    Z = R_i / R
    logger.info("Z (веса по разбросу) = %s", np.round(Z, 4))

    W = (V + Z) / 2.0
    logger.info("W (обобщённые веса) = %s", np.round(W, 4))

    E_ij = P * W
    E_j = E_ij.sum(axis=1)

    ranking = sorted(
        zip(config.alternatives, E_j.tolist()),
        key=lambda kv: kv[1],
        reverse=True,
    )

    return ComplexEvalResult(
        alternatives=list(config.alternatives),
        criteria=[c.code for c in config.criteria],
        raw_matrix=P,
        v_expert_avg=V,
        r_spread=R_i,
        z_spread_weights=Z,
        w_combined=W,
        weighted_matrix=E_ij,
        totals=E_j,
        ranking=ranking,
    )


def build_tsisa_config() -> tuple[np.ndarray, ComplexEvalConfig]:
    criteria = [
        Criterion("K1", "Стоимость", "min"),
        Criterion("K2", "Объективность изложения", "max", vark_axis="R"),
        Criterion("K3", "Поддержка средств тестирования", "max", vark_axis="K"),
        Criterion("K4", "Лёгкость и простота использования", "max", vark_axis="V"),
        Criterion("K5", "Соответствие VARK-профилю", "max"),
    ]

    raw = np.array([
        [300, 3, 0, 4, 0.70],
        [500, 3, 1, 4, 0.55],
        [400, 1, 1, 5, 0.90],
        [250, 3, 0, 2, 0.30],
    ], dtype=float)

    directions = [c.direction for c in criteria]
    P = normalize_matrix(raw, directions)

    experts = [
        ExpertWeights("Преподаватель", (0.35, 0.15, 0.10, 0.30, 0.10)),
        ExpertWeights("Методист",      (0.15, 0.30, 0.10, 0.15, 0.30)),
    ]

    config = ComplexEvalConfig(
        criteria=criteria,
        experts=experts,
        alternatives=["Y1", "Y2", "Y3", "Y4"],
    )
    return P, config


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _serialize(result: ComplexEvalResult, config: ComplexEvalConfig) -> dict:
    return {
        "criteria": [
            {"code": c.code, "name": c.name, "direction": c.direction, "vark_axis": c.vark_axis}
            for c in config.criteria
        ],
        "experts": [asdict(e) for e in config.experts],
        "alternatives": result.alternatives,
        "matrix_normalized": result.raw_matrix.round(4).tolist(),
        "v_expert_avg": result.v_expert_avg.round(4).tolist(),
        "r_spread": result.r_spread.round(4).tolist(),
        "z_spread_weights": result.z_spread_weights.round(4).tolist(),
        "w_combined": result.w_combined.round(4).tolist(),
        "weighted_matrix": result.weighted_matrix.round(4).tolist(),
        "totals": result.totals.round(4).tolist(),
        "ranking": [{"alternative": a, "score": round(s, 4)} for a, s in result.ranking],
        "best": result.ranking[0][0],
    }


def _print_report(result: ComplexEvalResult, config: ComplexEvalConfig) -> None:
    sep = "=" * 62
    print(sep)
    print("МЕТОД КОМПЛЕКСНОЙ ОЦЕНКИ — подбор учебной литературы (VARK+LLM)")
    print(sep)

    header = "Критерий".ljust(12) + "V".rjust(8) + "Z".rjust(8) + "W".rjust(8)
    print(header)
    for i, c in enumerate(config.criteria):
        print(
            f"{c.code + ' ' + c.name[:9]:<12}"
            f"{result.v_expert_avg[i]:>8.3f}"
            f"{result.z_spread_weights[i]:>8.3f}"
            f"{result.w_combined[i]:>8.3f}"
        )

    print("-" * 62)
    print("Взвешенные оценки E_ij:")
    header = "Альт".ljust(6) + "".join(f"{c.code:>9}" for c in config.criteria) + "TOTAL".rjust(9)
    print(header)
    for i, alt in enumerate(result.alternatives):
        row = f"{alt:<6}" + "".join(f"{v:>9.3f}" for v in result.weighted_matrix[i])
        row += f"{result.totals[i]:>9.3f}"
        print(row)

    print("-" * 62)
    print("ИТОГОВЫЙ РЕЙТИНГ:")
    for place, (alt, score) in enumerate(result.ranking, start=1):
        marker = "  <-- РЕКОМЕНДОВАНО" if place == 1 else ""
        print(f"  {place}. {alt}: {score:.4f}{marker}")
    print(sep)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Метод комплексной оценки (ТСиСА 4.2) для СППР подбора литературы.",
    )
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Путь для сохранения JSON-отчёта.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Подробный лог.")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)
    logger.info("Запуск метода комплексной оценки.")

    matrix, config = build_tsisa_config()
    result = compute_complex_evaluation(matrix, config)
    _print_report(result, config)

    if args.output:
        payload = _serialize(result, config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("JSON-отчёт сохранён: %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
