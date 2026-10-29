from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class Direction(str, Enum):
    MIN = "min"
    MAX = "max"


@dataclass(frozen=True)
class Criterion:
    code: str
    name: str
    direction: Direction
    unit: str = ""


@dataclass(frozen=True)
class ExpertWeights:
    name: str
    role: str
    weights: tuple[float, ...]


@dataclass(frozen=True)
class Book:
    code: str
    title: str
    author: str
    year: int
    book_type: str
    scores: tuple[float, ...]


@dataclass
class ComplexEvalConfig:
    criteria: list[Criterion]
    experts: list[ExpertWeights]
    alternatives: list[str]
    alpha: float = 0.5

    def validate(self) -> None:
        m = len(self.criteria)
        if m == 0:
            raise ValueError("Список критериев пуст")
        for e in self.experts:
            if len(e.weights) != m:
                raise ValueError(
                    f"Эксперт {e.name}: {len(e.weights)} весов, ожидалось {m}"
                )
            if not np.isclose(sum(e.weights), 1.0, atol=1e-6):
                raise ValueError(
                    f"Эксперт {e.name}: сумма весов = {sum(e.weights)}, ожидалось 1.0"
                )
        if not (0.0 <= self.alpha <= 1.0):
            raise ValueError(f"alpha={self.alpha} вне [0,1]")
