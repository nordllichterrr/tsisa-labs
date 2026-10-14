#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog, minimize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pr05")


@dataclass(frozen=True)
class Criterion:
    name: str
    coeffs: NDArray[np.float64]


@dataclass(frozen=True)
class Constraint:
    A_ub: NDArray[np.float64]
    b_ub: NDArray[np.float64]


@dataclass(frozen=True)
class OptimizationProblem:
    criteria: tuple[Criterion, Criterion]
    constraint: Constraint
    n_vars: int
    alpha: tuple[float, float] = (0.5, 0.5)
    bounds: tuple[tuple[float, float], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.criteria) != 2:
            raise ValueError("Ожидается ровно два критерия.")
        if not np.isclose(sum(self.alpha), 1.0):
            raise ValueError(f"Сумма весов должна быть 1.0, получено {sum(self.alpha)}.")
        if self.constraint.A_ub.shape[1] != self.n_vars:
            raise ValueError("Размерность A_ub не совпадает с числом переменных.")
        if len(self.bounds) != self.n_vars:
            raise ValueError("bounds должен содержать n_vars элементов.")


@dataclass
class Solution:
    method: str
    status: str
    x: NDArray[np.float64]
    f1: float
    f2: float
    scalarized: float | None = None
    deviation: float | None = None
    slack: NDArray[np.float64] | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["x"] = self.x.tolist()
        if self.slack is not None:
            d["slack"] = self.slack.tolist()
        return d


class TwoCriterionSolver:
    def __init__(self, problem: OptimizationProblem) -> None:
        self.p = problem
        self._F_star: NDArray[np.float64] | None = None

    def _solve_single_criterion(self, crit: Criterion) -> Solution:
        res = linprog(
            c=-crit.coeffs,
            A_ub=self.p.constraint.A_ub,
            b_ub=self.p.constraint.b_ub,
            bounds=self.p.bounds,
            method="highs",
        )
        if not res.success:
            raise RuntimeError(f"LP для '{crit.name}' не решена: {res.message}")

        x = res.x
        f1 = float(self.p.criteria[0].coeffs @ x)
        f2 = float(self.p.criteria[1].coeffs @ x)
        slack = self.p.constraint.b_ub - self.p.constraint.A_ub @ x

        logger.info(
            "Идеальная точка по '%s': x=%s, f1=%.4f, f2=%.4f",
            crit.name, np.round(x, 4).tolist(), f1, f2,
        )
        return Solution(
            method=f"LP по '{crit.name}'",
            status="optimal",
            x=x, f1=f1, f2=f2, slack=slack,
        )

    @property
    def F_star(self) -> NDArray[np.float64]:
        if self._F_star is None:
            s1 = self._solve_single_criterion(self.p.criteria[0])
            s2 = self._solve_single_criterion(self.p.criteria[1])
            self._F_star = np.array([s1.f1, s2.f2], dtype=np.float64)
            logger.info("F* = (%.4f, %.4f)", *self._F_star)
        return self._F_star

    def solve_min_deviation(self) -> Solution:
        F_star = self.F_star
        c1 = self.p.criteria[0].coeffs
        c2 = self.p.criteria[1].coeffs

        scale1 = max(abs(F_star[0]), 1.0)
        scale2 = max(abs(F_star[1]), 1.0)

        def objective(x: NDArray[np.float64]) -> float:
            f1 = c1 @ x
            f2 = c2 @ x
            d1 = (f1 - F_star[0]) / scale1
            d2 = (f2 - F_star[1]) / scale2
            return float(d1 * d1 + d2 * d2)

        constraints = [
            {"type": "ineq", "fun": lambda x, A=A, b=b: b - A @ x}
            for A, b in [(self.p.constraint.A_ub, self.p.constraint.b_ub)]
        ]

        x0 = np.zeros(self.p.n_vars)
        res = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=self.p.bounds,
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 5000},
        )
        if not res.success:
            logger.warning("SLSQP не сошёлся: %s. Пробуем другую стартовую точку.", res.message)
            x0 = np.full(self.p.n_vars, 1.0)
            res = minimize(
                objective,
                x0,
                method="SLSQP",
                bounds=self.p.bounds,
                constraints=constraints,
                options={"ftol": 1e-12, "maxiter": 5000},
            )
        if not res.success:
            raise RuntimeError(f"SLSQP не сошёлся: {res.message}")

        x = res.x
        f1 = float(c1 @ x)
        f2 = float(c2 @ x)
        slack = self.p.constraint.b_ub - self.p.constraint.A_ub @ x
        return Solution(
            method="Метод минимального отклонения",
            status="optimal",
            x=x, f1=f1, f2=f2,
            deviation=float(res.fun),
            slack=slack,
        )

    def solve_additive_convolution(self) -> Solution:
        a1, a2 = self.p.alpha
        c = a1 * self.p.criteria[0].coeffs + a2 * self.p.criteria[1].coeffs
        res = linprog(
            c=-c,
            A_ub=self.p.constraint.A_ub,
            b_ub=self.p.constraint.b_ub,
            bounds=self.p.bounds,
            method="highs",
        )
        if not res.success:
            raise RuntimeError(f"LP (свёртка) не решена: {res.message}")

        x = res.x
        f1 = float(self.p.criteria[0].coeffs @ x)
        f2 = float(self.p.criteria[1].coeffs @ x)
        slack = self.p.constraint.b_ub - self.p.constraint.A_ub @ x
        return Solution(
            method="Метод аддитивной свёртки",
            status="optimal",
            x=x, f1=f1, f2=f2,
            scalarized=float(a1 * f1 + a2 * f2),
            slack=slack,
        )


def build_variant_15() -> OptimizationProblem:
    c1 = np.array([55.0, 20.0, 43.0, 11.0])
    c2 = np.array([6.0, 5.0, 4.0, 3.0])
    A = np.array([
        [6.0, 4.0, 9.0, 5.0],
        [12.0, 2.0, 3.0, 8.0],
        [7.0, 5.0, 10.0, 6.0],
    ])
    b = np.array([147.0, 150.0, 135.0])
    return OptimizationProblem(
        criteria=(Criterion("f1", c1), Criterion("f2", c2)),
        constraint=Constraint(A_ub=A, b_ub=b),
        n_vars=4,
        alpha=(0.38, 0.62),
        bounds=tuple((0.0, None) for _ in range(4)),
    )


def format_solution(sol: Solution) -> str:
    lines: list[str] = []
    lines.append(sol.method)
    lines.append(f"x1 = {sol.x[0]:.4f}")
    lines.append(f"x2 = {sol.x[1]:.4f}")
    lines.append(f"x3 = {sol.x[2]:.4f}")
    lines.append(f"x4 = {sol.x[3]:.4f}")
    lines.append(f"f1 = {sol.f1:.4f}")
    lines.append(f"f2 = {sol.f2:.4f}")
    if sol.scalarized is not None:
        lines.append(f"F  = {sol.scalarized:.4f} (alpha1*f1 + alpha2*f2)")
    if sol.deviation is not None:
        lines.append(f"D  = {sol.deviation:.4f} (нормированное отклонение)")
    if sol.slack is not None:
        for i, s in enumerate(sol.slack, start=1):
            marker = " (active)" if abs(s) < 1e-6 else ""
            lines.append(f"constraint {i}: {s:.4f}{marker}")
    return "\n".join(lines)


def print_solution(sol: Solution) -> None:
    print(format_solution(sol))
    print()


def build_report(
    problem: OptimizationProblem,
    F_star: NDArray[np.float64],
    sol_min_dev: Solution,
    sol_add: Solution,
) -> str:
    a1, a2 = problem.alpha
    lines: list[str] = []
    lines.append("PR-05. Многокритериальная оптимизация. Вариант 15")
    lines.append("")
    lines.append("Постановка задачи:")
    lines.append("  f1 = 55x1 + 20x2 + 43x3 + 11x4 -> max")
    lines.append("  f2 =  6x1 +  5x2 +  4x3 +  3x4 -> max")
    lines.append("  6x1 + 4x2 +  9x3 + 5x4 <= 147")
    lines.append(" 12x1 + 2x2 +  3x3 + 8x4 <= 150")
    lines.append("  7x1 + 5x2 + 10x3 + 6x4 <= 135")
    lines.append("  x1, x2, x3, x4 >= 0")
    lines.append(f"  alpha1 = {a1}, alpha2 = {a2}")
    lines.append("")
    lines.append(f"Идеальная точка F* = (f1*={F_star[0]:.4f}, f2*={F_star[1]:.4f})")
    lines.append("")
    lines.append("Метод 1. Минимальное отклонение от идеальной точки")
    lines.append(format_solution(sol_min_dev))
    lines.append("")
    lines.append("Метод 2. Аддитивная свёртка")
    lines.append(format_solution(sol_add))
    lines.append("")
    return "\n".join(lines)


def export_json(path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(kwargs, f, ensure_ascii=False, indent=2)
    logger.info("JSON сохранён: %s", path)


def export_txt(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    logger.info("TXT сохранён: %s", path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR-05: двухкритериальная оптимизация (вариант 15).",
    )
    parser.add_argument(
        "--json", type=Path, default=Path("results/pr05_variant15.json"),
        help="Путь для сохранения JSON с результатами.",
    )
    parser.add_argument(
        "--txt", type=Path, default=Path("results/pr05_variant15.txt"),
        help="Путь для сохранения TXT с отчётом.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Не печатать отчёт в stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logger.info("Запуск PR-05, вариант 15")

    problem = build_variant_15()
    solver = TwoCriterionSolver(problem)

    F_star = solver.F_star
    sol_min_dev = solver.solve_min_deviation()
    sol_add = solver.solve_additive_convolution()

    report = build_report(problem, F_star, sol_min_dev, sol_add)

    if not args.quiet:
        print(report)

    export_json(
        args.json,
        variant=15,
        ideal_point={"f1": float(F_star[0]), "f2": float(F_star[1])},
        min_deviation=sol_min_dev.to_dict(),
        additive_convolution=sol_add.to_dict(),
    )
    export_txt(args.txt, report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
