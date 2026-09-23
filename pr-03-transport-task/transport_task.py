"""Практическая работа №3. Вариант 15 (картофель)."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from scipy.optimize import linprog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("transport_task")


@dataclass(frozen=True)
class TransportProblem:
    cost: np.ndarray
    supply: np.ndarray
    demand: np.ndarray
    supply_names: list[str] = field(default_factory=list)
    demand_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.cost.shape != (len(self.supply), len(self.demand)):
            raise ValueError("Размеры матрицы стоимости и векторов не совпадают")
        if not self.supply_names:
            object.__setattr__(
                self, "supply_names",
                [f"Кооператив №{i+1}" for i in range(len(self.supply))],
            )
        if not self.demand_names:
            object.__setattr__(
                self, "demand_names",
                [f"Склад №{j+1}" for j in range(len(self.demand))],
            )

    @property
    def is_balanced(self) -> bool:
        return bool(np.isclose(self.supply.sum(), self.demand.sum()))

    @property
    def total_supply(self) -> float:
        return float(self.supply.sum())

    @property
    def total_demand(self) -> float:
        return float(self.demand.sum())


class TransportSolver:
    def __init__(self, problem: TransportProblem) -> None:
        if not problem.is_balanced:
            raise ValueError("Задача не сбалансирована")
        self.problem = problem
        self._m, self._n = problem.cost.shape

    def _build_constraints(self) -> Tuple[np.ndarray, np.ndarray]:
        m, n = self._m, self._n
        a_eq = np.zeros((m + n, m * n), dtype=float)
        for i in range(m):
            a_eq[i, i * n:(i + 1) * n] = 1.0
        for j in range(n):
            a_eq[m + j, j::n] = 1.0
        b_eq = np.concatenate([self.problem.supply, self.problem.demand])
        return a_eq, b_eq

    def solve(self):
        m, n = self._m, self._n
        c = self.problem.cost.flatten().astype(float)
        a_eq, b_eq = self._build_constraints()
        logger.info("linprog: %d переменных, %d ограничений", m * n, m + n)
        result = linprog(c=c, A_eq=a_eq, b_eq=b_eq,
                         bounds=(0, None), method="highs")
        if not result.success:
            raise RuntimeError("Задача не решена: " + result.message)
        plan = result.x.reshape(m, n)
        plan = np.where(np.abs(plan) < 1e-9, 0.0, plan)
        return TransportSolution(
            problem=self.problem,
            plan=plan,
            total_cost=float(result.fun),
            status=result.message,
        )


@dataclass
class TransportSolution:
    problem: TransportProblem
    plan: np.ndarray
    total_cost: float
    status: str

    def plan_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(
            self.plan,
            index=self.problem.supply_names,
            columns=self.problem.demand_names,
        )
        df["Производство"] = self.problem.supply
        return df

    def cost_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(
            self.problem.cost,
            index=self.problem.supply_names,
            columns=self.problem.demand_names,
        )
        df["Производство"] = self.problem.supply
        return df

    def validation_dataframe(self) -> pd.DataFrame:
        rows_shipped = self.plan.sum(axis=1)
        cols_received = self.plan.sum(axis=0)
        df = pd.DataFrame({
            "Пункт": self.problem.supply_names + self.problem.demand_names,
            "Тип": ["Производство"] * len(self.problem.supply)
                   + ["Потребность"] * len(self.problem.demand),
            "План": np.concatenate([rows_shipped, cols_received]),
            "Цель": np.concatenate([self.problem.supply, self.problem.demand]),
        })
        df["Отклонение"] = df["План"] - df["Цель"]
        return df

    def save(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.plan_dataframe().to_csv(out_dir / "solution.csv", sep=";")
        report_path = out_dir / "report.txt"
        with report_path.open("w", encoding="utf-8") as f:
            f.write("ОТЧЁТ ПО ТРАНСПОРТНОЙ ЗАДАЧЕ (вариант 15)\n\n")
            f.write("Статус: " + self.status + "\n")
            f.write("Суммарные затраты: {:.4f} тыс. руб.\n\n"
                    .format(self.total_cost))
            f.write("Матрица стоимостей:\n")
            f.write(self.cost_dataframe().to_string())
            f.write("\n\nОптимальный план перевозок:\n")
            f.write(self.plan_dataframe().to_string())
            f.write("\n\nПроверка ограничений:\n")
            f.write(self.validation_dataframe().to_string())
            f.write("\n")
        logger.info("Отчёт сохранён: %s", report_path)


def build_variant_15() -> TransportProblem:
    cost = np.array([
        [77.0, 80.0, 48.0],
        [65.0, 42.0, 79.0],
        [85.0, 51.0, 52.0],
        [60.0, 78.0, 76.0],
    ])
    supply = np.array([95.0, 150.0, 125.0, 140.0])
    demand = np.array([155.0, 180.0, 175.0])
    return TransportProblem(
        cost=cost,
        supply=supply,
        demand=demand,
        supply_names=[
            "Кооператив №1",
            "Кооператив №2",
            "Кооператив №3",
            "Кооператив №4",
        ],
        demand_names=["Склад №1", "Склад №2", "Склад №3"],
    )


def main() -> int:
    logger.info("Практическая работа №3. Вариант 15.")
    problem = build_variant_15()
    logger.info(
        "Производство=%.2f, потребности=%.2f, сбалансирована=%s",
        problem.total_supply, problem.total_demand, problem.is_balanced,
    )
    solution = TransportSolver(problem).solve()

    print("\nОПТИМАЛЬНЫЙ ПЛАН ПЕРЕВОЗОК\n")
    print(solution.plan_dataframe().to_string())

    print("\nПРОВЕРКА ОГРАНИЧЕНИЙ\n")
    print(solution.validation_dataframe().to_string())

    print("\nМИНИМАЛЬНЫЕ СУММАРНЫЕ ЗАТРАТЫ: "
          + "{:.2f}".format(solution.total_cost) + " тыс. руб.\n")

    out_dir = Path(__file__).parent / "output"
    solution.save(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
