from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from scipy.optimize import linprog, OptimizeResult


# Неизменяемый датакласс, описывающий задачу ЛП в стандартной форме
@dataclass(frozen=True)
class LPProblem:
    # Вектор коэффициентов целевой функции
    c: np.ndarray
    # Матрица коэффициентов ограничений (A_ub * x <= b_ub)
    A_ub: np.ndarray
    # Вектор правых частей ограничений
    b_ub: np.ndarray
    # Границы изменения переменных: список пар (нижняя, верхняя)
    bounds: Sequence[tuple[float | None, float | None]]


# Неизменяемый датакласс, описывающий решение задачи ЛП
@dataclass(frozen=True)
class LPSolution:
    # Вектор найденных значений переменных
    x: np.ndarray
    # Достигнутое значение целевой функции
    objective: float
    # Числовой код статуса решения от scipy
    status: int
    # Текстовое сообщение о статусе решения
    message: str
    # Вектор невязок ограничений (b_ub - A_ub @ x)
    slack: np.ndarray


# Функция решения задачи ЛП; sense = "min" или "max"
def solve_lp(problem: LPProblem, sense: str = "min") -> LPSolution:
    # Валидация направления оптимизации
    if sense not in {"min", "max"}:
        # Выброс исключения при некорректном значении sense
        raise ValueError(f"Unknown sense: {sense}")

    # Если нужен максимум — инвертируем знаки коэффициентов, т.к. linprog минимизирует
    c = problem.c if sense == "min" else -problem.c

    # Запуск симплекс-метода (HiGHS) с передачей коэффициентов, ограничений и границ
    result: OptimizeResult = linprog(
        c=c,
        A_ub=problem.A_ub,
        b_ub=problem.b_ub,
        bounds=problem.bounds,
        method="highs",
    )

    # Если решатель не нашёл решения — выбрасываем исключение с сообщением
    if not result.success:
        raise RuntimeError(f"LP solver failed: {result.message}")

    # Возвращаем значение ЦФ с учётом исходного направления (max/min)
    objective = float(result.fun if sense == "min" else -result.fun)
    # Вычисляем невязки ограничений: насколько левая часть меньше правой
    slack = problem.b_ub - problem.A_ub @ result.x

    # Формируем и возвращаем неизменяемый объект результата
    return LPSolution(
        x=np.asarray(result.x, dtype=float),
        objective=objective,
        status=int(result.status),
        message=str(result.message),
        slack=np.asarray(slack, dtype=float),
    )


# Функция построения двойственной задачи по прямой
def build_dual(primal: LPProblem) -> LPProblem:
    # Возвращаем новую задачу ЛП с транспонированной матрицей и заменой ролей c и b
    return LPProblem(
        # Коэффициенты ЦФ двойственной = правые части прямой
        c=primal.b_ub.copy(),
        # Матрица ограничений двойственной = -A^T (знаки меняются из-за >=)
        A_ub=-primal.A_ub.T,
        # Правые части двойственной = -c прямой
        b_ub=-primal.c.copy(),
        # Число переменных двойственной = число ограничений прямой; все >= 0
        bounds=[(0.0, None)] * primal.A_ub.shape[0],
    )


# Утилита форматирования вектора решения для печати
def format_vector(name: str, values: np.ndarray) -> str:
    # Формируем строку вида "x1=..., x2=..., ..." с 6 знаками после запятой
    parts = ", ".join(f"{name}{i + 1}={v:.6f}" for i, v in enumerate(values))
    # Возвращаем строку, обёрнутую в квадратные скобки
    return f"[{parts}]"


# Точка входа скрипта
def main() -> None:
    # Формируем исходную (прямую) задачу по варианту 15
    primal = LPProblem(
        # Коэффициенты ЦФ: 3x1 + 4x2 + 2x3
        c=np.array([3.0, 4.0, 2.0]),
        # Матрица ограничений 4x3
        A_ub=np.array(
            [
                [1.0, 4.0, 2.0],
                [2.0, 1.0, 3.0],
                [1.0, 5.0, 1.0],
                [5.0, 1.0, 2.0],
            ]
        ),
        # Правые части ограничений
        b_ub=np.array([25.0, 31.0, 37.0, 39.0]),
        # Условие неотрицательности x1, x2, x3 >= 0
        bounds=[(0.0, None)] * 3,
    )

    # Строим двойственную задачу на основе прямой
    dual = build_dual(primal)

    # Решаем прямую задачу на максимум
    primal_sol = solve_lp(primal, sense="max")
    # Решаем двойственную задачу на минимум
    dual_sol = solve_lp(dual, sense="min")

    # Печатаем решение прямой задачи: значения x и оптимум ЦФ
    print(f"Primal: {format_vector('x', primal_sol.x)} obj={primal_sol.objective:.6f}")
    # Печатаем решение двойственной задачи: значения y и оптимум ЦФ
    print(f"Dual:   {format_vector('y', dual_sol.x)} obj={dual_sol.objective:.6f}")

    # Считаем разрыв двойственности между оптимумами прямой и двойственной задач
    duality_gap = abs(primal_sol.objective - dual_sol.objective)
    # Проверяем теорему двойственности: расхождение не должно превышать 1e-6
    if duality_gap > 1e-6:
        raise AssertionError(f"Duality gap violated: {duality_gap:.2e}")

    # Проходим по всем ресурсам и печатаем их невязки и двойственные оценки
    for idx, (slack, y) in enumerate(zip(primal_sol.slack, dual_sol.x), start=1):
        # Ресурс считается дефицитным, если невязка близка к нулю
        binding = abs(slack) < 1e-6
        # Выводим информацию по ресурсу: невязка, двойственная оценка, дефицитность
        print(f"Resource {idx}: slack={slack:.6f} dual={y:.6f} binding={binding}")

if __name__ == "__main__":
    main()