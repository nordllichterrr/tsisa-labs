from __future__ import annotations
import math

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pulp
from pulp import LpProblem, LpVariable, LpMaximize, value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProductionResult:
    """Неизменяемый контейнер результата решения задачи ЦЛП."""
    task_name: str
    status: str
    optimal_value: float
    decisions: Dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [f"{'='*60}", f"  {self.task_name}", f"{'='*60}"]
        lines.append(f"  Статус          : {self.status}")
        lines.append(f"  Значение ЦФ     : {self.optimal_value:,.2f}")
        lines.append("  Решение:")
        for var, val in self.decisions.items():
            lines.append(f"    {var:<30} = {val:>12,.2f}")
        lines.append("")
        return "\n".join(lines)


class IntegerLPWorker:
    """Обёртка над PuLP для решения задач целочисленного ЛП."""

    def __init__(self, solver: Optional[pulp.LpSolver] = None) -> None:
        self._solver = solver or pulp.PULP_CBC_CMD(msg=False)

    def solve(
        self,
        name: str,
        objective: pulp.LpAffineExpression,
        constraints: List[pulp.LpConstraint],
        variables: Dict[str, pulp.LpVariable],
    ) -> ProductionResult:
        prob = LpProblem(name=name, sense=LpMaximize)
        prob += objective

        for c in constraints:
            prob += c

        logger.info("Решение задачи '%s' ...", name)
        prob.solve(self._solver)

        status = pulp.LpStatus[prob.status]
        obj_val = value(prob.objective) or 0.0

        decisions = {var_name: (var.value() or 0.0)
                     for var_name, var in variables.items()}

        return ProductionResult(
            task_name=name,
            status=status,
            optimal_value=obj_val,
            decisions=decisions,
        )


def solve_task_1_furniture(worker: IntegerLPWorker) -> ProductionResult:
    # x1 — стулья, x2 — столы; 100*x1 + 400*x2 -> max
    x1 = LpVariable("стулья", lowBound=0, cat="Integer")
    x2 = LpVariable("столы", lowBound=0, cat="Integer")

    return worker.solve(
        name="Задача_1_Мебель",
        objective=100 * x1 + 400 * x2,
        constraints=[
            3 * x1 + 7 * x2 <= 420,   # древесина
            2 * x1 + 8 * x2 <= 400,   # рабочее время
        ],
        variables={"стулья": x1, "столы": x2},
    )


def solve_task_2_clothing(worker: IntegerLPWorker) -> ProductionResult:
    # x1 — женские, x2 — мужские; 1000*x1 + 2000*x2 -> max
    x1 = LpVariable("женские_костюмы", lowBound=0, cat="Integer")
    x2 = LpVariable("мужские_костюмы", lowBound=60, cat="Integer")

    return worker.solve(
        name="Задача_2_Костюмы",
        objective=1000 * x1 + 2000 * x2,
        constraints=[
            1 * x1 + 3.5 * x2 <= 350,   # шерсть
            2 * x1 + 0.5 * x2 <= 240,   # лавсан
            1 * x1 + 1 * x2 <= 150,     # трудозатраты
            x2 >= 60,                    # контрактный минимум
        ],
        variables={"женские_костюмы": x1, "мужские_костюмы": x2},
    )


def solve_task_3_glass(worker: IntegerLPWorker) -> ProductionResult:
    # x1 — вазы, x2 — графины; 700*x1 + 560*x2 -> max
    x1 = LpVariable("вазы", lowBound=0, upBound=200, cat="Integer")
    x2 = LpVariable("графины", lowBound=0, cat="Integer")

    return worker.solve(
        name="Задача_3_Стекло",
        objective=700 * x1 + 560 * x2,
        constraints=[
            20 * x1 + 18 * x2 <= 3000,   # кобальт (г)
            13 * x1 + 10 * x2 <= 1200,   # золото (г)
            x1 <= 200,                    # спрос на вазы
        ],
        variables={"вазы": x1, "графины": x2},
    )


def main() -> None:
    worker = IntegerLPWorker()

    tasks = [
        solve_task_1_furniture,
        solve_task_2_clothing,
        solve_task_3_glass,
    ]

    results = []
    for task_fn in tasks:
        result = task_fn(worker)
        results.append(result)
        print(result)

    assert round(results[0].optimal_value) == 20000, f"Задача 1: получено {results[0].optimal_value}"
    assert round(results[1].optimal_value) == 230000, f"Задача 2: получено {results[1].optimal_value}"
    assert round(results[2].optimal_value) == 67200, f"Задача 3: получено {results[2].optimal_value}"
    logger.info("Все задачи решены и проверены успешно.")


if __name__ == "__main__":
    main()
