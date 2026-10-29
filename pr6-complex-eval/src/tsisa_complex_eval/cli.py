from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .application import compute_complex_evaluation, sensitivity_analysis
from .infrastructure import (
    books_to_matrix,
    load_books,
    load_config,
    save_report,
)

logger = logging.getLogger("complex_eval")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


def _serialize(result, config) -> dict:
    return {
        "schema_version": "1.0.0",
        "criteria": [
            {"code": c.code, "name": c.name, "direction": c.direction.value}
            for c in config.criteria
        ],
        "experts": [
            {"name": e.name, "role": e.role, "weights": list(e.weights)}
            for e in config.experts
        ],
        "alpha": config.alpha,
        "normalized": result.normalized.round(4).tolist(),
        "v_expert_avg": result.v_expert_avg.round(4).tolist(),
        "z_spread_weights": result.z_spread_weights.round(4).tolist(),
        "w_combined": result.w_combined.round(4).tolist(),
        "totals": result.totals.round(4).tolist(),
        "ranking": [
            {"alternative": a, "score": round(s, 4)}
            for a, s in result.ranking
        ],
        "best": result.ranking[0][0],
    }


def _print_report(result, config) -> None:
    sep = "=" * 64
    print(sep)
    print("КОМПЛЕКСНАЯ ОЦЕНКА УЧЕБНОЙ ЛИТЕРАТУРЫ (СППР VARK+LLM)")
    print(sep)
    print(f"{'Критерий':<12}{'V':>8}{'Z':>8}{'W':>8}")
    for i, c in enumerate(config.criteria):
        print(
            f"{c.code + ' ' + c.name[:9]:<12}"
            f"{result.v_expert_avg[i]:>8.3f}"
            f"{result.z_spread_weights[i]:>8.3f}"
            f"{result.w_combined[i]:>8.3f}"
        )
    print(sep)
    print("Взвешенные оценки:")
    print(f"{'Книга':<6}" + "".join(f"{c.code:>9}" for c in config.criteria) + f"{'Итог':>9}")
    for i, alt in enumerate(result.alternatives):
        row = f"{alt:<6}" + "".join(f"{v:>9.3f}" for v in result.weighted[i])
        row += f"{result.totals[i]:>9.3f}"
        print(row)
    print(sep)
    print("Итоговый рейтинг:")
    for place, (alt, score) in enumerate(result.ranking, start=1):
        marker = "  <-- РЕКОМЕНДОВАНО" if place == 1 else ""
        print(f"  {place}. {alt}: {score:.4f}{marker}")
    print(sep)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Метод комплексной оценки для СППР подбора литературы"
    )
    parser.add_argument("--books", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    books = load_books(args.books)
    matrix = books_to_matrix(books)
    config = load_config(args.config)
    config.alternatives = [b.code for b in books]

    result = compute_complex_evaluation(matrix, config)
    _print_report(result, config)

    if args.sensitivity:
        print("\nSensitivity analysis по alpha:")
        for row in sensitivity_analysis(matrix, config):
            print(f"  alpha={row['alpha']:.1f} -> winner={row['winner']}")

    if args.output:
        payload = _serialize(result, config)
        if args.sensitivity:
            payload["sensitivity"] = sensitivity_analysis(matrix, config)
        save_report(payload, args.output)
        logger.info("Отчёт сохранён в %s", args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
