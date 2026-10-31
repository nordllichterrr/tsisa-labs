import numpy as np
from typing import List, Tuple, Dict

# Средние случайные индексы согласованности (СИ) по Саати
RANDOM_INDEX = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49
}


class AHP:
    """Метод анализа иерархий (МАИ) для многокритериального выбора."""

    def __init__(self) -> None:
        self.criteria_names: List[str] = []
        self.alternatives_names: List[str] = []
        self.criteria_matrix: np.ndarray | None = None
        self.alternative_matrices: Dict[str, np.ndarray] = {}
        self.criteria_weights: np.ndarray | None = None
        self.alternative_scores: Dict[str, np.ndarray] = {}
        self.global_priorities: np.ndarray | None = None

    def set_criteria(self, names: List[str]) -> None:
        self.criteria_names = names

    def set_alternatives(self, names: List[str]) -> None:
        self.alternatives_names = names

    def set_criteria_matrix(self, matrix: List[List[float]]) -> None:
        m = np.array(matrix, dtype=float)
        n = m.shape[0]
        if m.shape != (n, n) or n != len(self.criteria_names):
            raise ValueError("Размерность матрицы критериев не совпадает с количеством критериев.")
        self.criteria_matrix = m

    def add_alternative_matrix(self, criterion: str, matrix: List[List[float]]) -> None:
        if criterion not in self.criteria_names:
            raise ValueError(f"Критерий '{criterion}' не найден.")
        m = np.array(matrix, dtype=float)
        n = m.shape[0]
        if m.shape != (n, n) or n != len(self.alternatives_names):
            raise ValueError(f"Размерность матрицы для '{criterion}' не совпадает с числом альтернатив.")
        self.alternative_matrices[criterion] = m

    @staticmethod
    def _priority_vector(matrix: np.ndarray) -> Tuple[np.ndarray, float]:
        n = matrix.shape[0]
        if n == 1:
            return np.array([1.0]), 0.0

        # Геометрическое среднее по строкам
        gmean = np.prod(matrix, axis=1) ** (1.0 / n)
        weights = gmean / gmean.sum()

        # λ_max и индекс согласованности
        weighted_sum = matrix @ weights
        lambda_max = float(np.mean(weighted_sum / weights))
        ci = (lambda_max - n) / (n - 1)
        ri = RANDOM_INDEX[n]
        cr = ci / ri if ri > 0 else 0.0
        return weights, cr

    def calculate_criteria_weights(self) -> Tuple[np.ndarray, float]:
        if self.criteria_matrix is None:
            raise ValueError("Матрица критериев не задана.")
        self.criteria_weights, cr = self._priority_vector(self.criteria_matrix)
        return self.criteria_weights, cr

    def calculate_alternative_scores(self) -> Dict[str, Tuple[np.ndarray, float]]:
        results: Dict[str, Tuple[np.ndarray, float]] = {}
        for c in self.criteria_names:
            if c not in self.alternative_matrices:
                raise ValueError(f"Отсутствует матрица для критерия '{c}'.")
            w, cr = self._priority_vector(self.alternative_matrices[c])
            self.alternative_scores[c] = w
            results[c] = (w, cr)
        return results

    def synthesize(self) -> np.ndarray:
        if self.criteria_weights is None or not self.alternative_scores:
            raise ValueError("Сначала вычислите веса критериев и локальные приоритеты.")
        n = len(self.alternatives_names)
        result = np.zeros(n)
        for i, c in enumerate(self.criteria_names):
            result += self.criteria_weights[i] * self.alternative_scores[c]
        self.global_priorities = result
        return result

    def best(self) -> str:
        if self.global_priorities is None:
            raise ValueError("Глобальные приоритеты не вычислены.")
        return self.alternatives_names[int(np.argmax(self.global_priorities))]


def main() -> None:
    print("=" * 70)
    print("ПР №7. МАИ. Вариант 15")
    print("Тема ВКР: СППР для подбора учебной литературы (VARK + LLM)")
    print("=" * 70)

    ahp = AHP()

    # --- 1. Иерархия ---
    criteria = [
        "K1: Соответствие стилю VARK",
        "K2: Соответствие цели изучения",
        "K3: Новизна издания",
        "K4: Соответствие ФГОС",
        "K5: Трудозатраты на чтение",
    ]
    alternatives = [
        "A1: Учебник 'Python для анализа данных' (2023)",
        "A2: Практикум 'Python: задачи и решения' (2021)",
        "A3: Монография 'Data Science: теория' (2019)",
    ]
    ahp.set_criteria(criteria)
    ahp.set_alternatives(alternatives)

    print("\n[1] Иерархия")
    for c in criteria:
        print(f"  - {c}")
    for a in alternatives:
        print(f"  * {a}")

    # --- 2. Матрица критериев ---
    # Веса из ЛР2/ЛР3: 0.35, 0.25, 0.15, 0.15, 0.10
    # Построим согласованную матрицу, близкую к этим весам
    criteria_matrix = [
        [1,    3,    5,    5,    7],
        [1/3,  1,    3,    3,    5],
        [1/5,  1/3,  1,    1,    3],
        [1/5,  1/3,  1,    1,    3],
        [1/7,  1/5,  1/3,  1/3,  1],
    ]
    ahp.set_criteria_matrix(criteria_matrix)
    weights, cr = ahp.calculate_criteria_weights()

    print("\n[2] Веса критериев (МАИ):")
    for c, w in zip(criteria, weights):
        print(f"  {c}: {w:.4f}")
    print(f"  CR = {cr:.4f} {'(OK)' if cr <= 0.10 else '(превышает 0.10!)'}")

    # --- 3. Матрицы альтернатив ---
    print("\n[3] Локальные приоритеты альтернатив по критериям:")

    alt_matrices = {
        criteria[0]: [  # K1: VARK -> A1 визуал/схемы лучше всего
            [1,   3,   5],
            [1/3, 1,   3],
            [1/5, 1/3, 1],
        ],
        criteria[1]: [  # K2: цель -> A1 и A2 практичнее
            [1,   1,   3],
            [1,   1,   3],
            [1/3, 1/3, 1],
        ],
        criteria[2]: [  # K3: новизна -> A1 новее всех
            [1,   3,   5],
            [1/3, 1,   3],
            [1/5, 1/3, 1],
        ],
        criteria[3]: [  # K4: ФГОС -> A1 лучше всего
            [1,   3,   5],
            [1/3, 1,   3],
            [1/5, 1/3, 1],
        ],
        criteria[4]: [  # K5: трудозатраты -> A2 и A3 легче (практикум)
            [1,   1/3, 1/2],
            [3,   1,   2],
            [2,   1/2, 1],
        ],
    }

    for c, m in alt_matrices.items():
        ahp.add_alternative_matrix(c, m)

    local = ahp.calculate_alternative_scores()
    for c, (w, cr_l) in local.items():
        print(f"\n  {c}")
        for a, val in zip(alternatives, w):
            print(f"    {a}: {val:.4f}")
        print(f"    CR = {cr_l:.4f} {'(OK)' if cr_l <= 0.10 else '(превышает 0.10!)'}")

    # --- 4. Синтез ---
    print("\n[4] Синтез глобальных приоритетов:")
    global_p = ahp.synthesize()
    for a, val in zip(alternatives, global_p):
        print(f"  {a}: {val:.4f}")

    # --- 5. Лучшая альтернатива ---
    best = ahp.best()
    print("\n[5] Наилучшая альтернатива:")
    print(f"  >>> {best} <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
