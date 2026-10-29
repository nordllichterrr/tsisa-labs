# PR6 — Метод комплексной оценки для СППР подбора учебной литературы

## Запуск

    export PYTHONPATH=src
    python -m tsisa_complex_eval.cli \
      --books data/books.json \
      --config configs/weights.yaml \
      --output reports/result.json \
      --sensitivity

## Флаги

- `--books` — JSON с книгами (альтернативами);
- `--config` — YAML с критериями и весами экспертов;
- `--output` — путь для JSON-отчёта;
- `--sensitivity` — прогон для α ∈ {0.3, 0.5, 0.7} (проверка устойчивости);
- `-v`, `--verbose` — подробные логи.

## Тесты

    export PYTHONPATH=src
    pytest tests/ -v

Покрыто: нормировка max/min, падение на нулевом max, полный пайплайн,
инвариант суммы обобщённых весов.

## Структура

    pr6-complex-eval/
    ├── src/tsisa_complex_eval/
    │   ├── domain.py          # сущности: Criterion, ExpertWeights, Book, Config
    │   ├── application.py     # математика: normalize, compute, sensitivity
    │   ├── infrastructure.py  # I/O: JSON, YAML
    │   └── cli.py             # CLI (argparse)
    ├── tests/test_application.py
    ├── data/books.json
    ├── configs/weights.yaml
    ├── reports/result.json
    ├── requirements.txt
    └── README.md

## Как работает метод

1. **Нормировка.** Для критериев `max` значение делится на максимум по
   столбцу; для `min` — минимум делится на значение. На выходе матрица
   `P ∈ [0, 1]`.
2. **Веса экспертов.** `V = mean(weights)` по всем ЛПР, покомпонентно.
3. **Веса по разбросу.** `R_i = max(P_i) − min(P_i)`, `Z = R_i / ΣR_i`.
   Чем сильнее оценки различаются, тем выше вес критерия.
4. **Обобщённые веса.** `W = α·V + (1−α)·Z`, по умолчанию α = 0.5.
5. **Взвешенные оценки.** `E_ij = P_ij · W_i`, итог `E_j = Σ_i E_ij`.
6. **Рейтинг.** Сортировка по `E_j` по убыванию; победитель — `argmax`.

## Результат на текущих данных

Победитель — **B2 «Python Crash Course»** (Э. Мэтиз). Sensitivity analysis
по α ∈ {0.3, 0.5, 0.7} даёт того же победителя, то есть выбор устойчив
к смешиванию весов экспертов и весов по разбросу.

## Требования

- Python 3.12+ (совместимо с 3.10+)
- NumPy ≥ 1.26
- PyYAML ≥ 6.0
- pytest ≥ 8.0
