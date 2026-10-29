from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from .domain import Book, ComplexEvalConfig, Criterion, Direction, ExpertWeights


def load_books(path: Path) -> list[Book]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Book(
            code=item["code"],
            title=item["title"],
            author=item["author"],
            year=item["year"],
            book_type=item["book_type"],
            scores=tuple(item["scores"]),
        )
        for item in raw["books"]
    ]


def books_to_matrix(books: list[Book]) -> np.ndarray:
    return np.array([b.scores for b in books], dtype=float)


def load_config(path: Path) -> ComplexEvalConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    criteria = [
        Criterion(
            code=c["code"],
            name=c["name"],
            direction=Direction(c["direction"]),
            unit=c.get("unit", ""),
        )
        for c in raw["criteria"]
    ]
    experts = [
        ExpertWeights(
            name=e["name"],
            role=e["role"],
            weights=tuple(e["weights"]),
        )
        for e in raw["experts"]
    ]
    return ComplexEvalConfig(
        criteria=criteria,
        experts=experts,
        alternatives=raw["alternatives"],
        alpha=raw.get("alpha", 0.5),
    )


def save_report(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
