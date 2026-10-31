import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

DB_PATH = Path(__file__).resolve().parent / 'books.db'

RANDOM_INDEX = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}
SAATY = [1, 2, 3, 4, 5, 6, 7, 8, 9]
TYPE_W = {'учебник': 1.0, 'практикум': 0.8, 'монография': 0.3, 'методичка': 0.2}


def saaty_from_ratio(ratio: float) -> float:
    if ratio <= 0:
        return 1.0
    if ratio >= 1:
        return float(min(SAATY, key=lambda s: abs(s - ratio)))
    inv = 1.0 / ratio
    return 1.0 / float(min(SAATY, key=lambda s: abs(s - inv)))


def build_pairwise(scores: List[float]) -> np.ndarray:
    n = len(scores)
    m = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                m[i, j] = saaty_from_ratio(scores[i] / scores[j])
    return m


def priority_vector(matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    n = matrix.shape[0]
    if n == 1:
        return np.array([1.0]), 0.0
    g = np.prod(matrix, axis=1) ** (1.0 / n)
    w = g / g.sum()
    lam = float(np.mean((matrix @ w) / w))
    ci = (lam - n) / (n - 1)
    ri = RANDOM_INDEX[n]
    cr = ci / ri if ri > 0 else 0.0
    return w, cr


def load_all(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row
    student = conn.execute('SELECT * FROM students LIMIT 1').fetchone()
    books = conn.execute("""
        SELECT b.*, GROUP_CONCAT(f.name, '|') AS formats
        FROM books b
        LEFT JOIN book_formats bf ON bf.book_id = b.book_id
        LEFT JOIN formats f ON f.format_id = bf.format_id
        GROUP BY b.book_id
    """).fetchall()
    crit = conn.execute('SELECT * FROM criteria ORDER BY criterion_id').fetchall()
    return student, books, crit


def filter_books(books):
    return [b for b in books if b['ebs'] == 1 and b['book_type'] in ('учебник', 'практикум')]


def score_k1(formats: str, dominant: str) -> float:
    fmts = set((formats or '').split('|'))
    return 1.0 if dominant in fmts else 0.2


def score_k2(has_practice: int, goal: str) -> float:
    if goal == 'экзамен' and has_practice == 1:
        return 1.0
    if goal == 'курсовая' and has_practice == 1:
        return 0.7
    return 0.4


def score_k3(year: int, lo: int, hi: int) -> float:
    return 1.0 if hi == lo else 0.1 + 0.9 * (year - lo) / (hi - lo)


def score_k4(book) -> float:
    return 0.5 * TYPE_W.get(book['book_type'], 0.2) + 0.5 * float(book['umo'])


def score_k5(pages: int, complexity: float, max_load: float) -> float:
    return 1.0 - (pages * complexity / max_load) * 0.9


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f'Нет базы {DB_PATH}. Сначала запусти init_db.py')
    conn = sqlite3.connect(DB_PATH)
    try:
        student, books, crit = load_all(conn)
        print(f'Студент: {student["full_name"]}, курс {student["course"]}, '
              f'VARK={student["vark_dominant"]}, цель={student["goal"]}')
        print(f'Книг в БД: {len(books)}')

        allowed = filter_books(books)
        print(f'Прошли G1–G4: {[b["book_id"] for b in allowed]}')

        if not allowed:
            raise SystemExit('Нет допустимых книг — ослабить ограничения.')

        lo = min(b['year'] for b in allowed)
        hi = max(b['year'] for b in allowed)
        max_load = max(b['pages'] * b['complexity'] for b in allowed)

        scores = []
        for b in allowed:
            scores.append([
                score_k1(b['formats'], student['vark_dominant']),
                score_k2(b['has_practice'], student['goal']),
                score_k3(b['year'], lo, hi),
                score_k4(b),
                score_k5(b['pages'], b['complexity'], max_load),
            ])
        scores = np.array(scores)

        weights = np.array([c['weight'] for c in crit])
        local = {}
        print('\nЛокальные приоритеты по критериям:')
        for i, c in enumerate(crit):
            m = build_pairwise(scores[:, i].tolist())
            pv, cr = priority_vector(m)
            local[c['criterion_id']] = pv
            print(f'  {c["criterion_id"]} {c["name"]} (w={c["weight"]}): '
                  f'{np.round(pv, 4)}  CR={cr:.4f}')

        local_matrix = np.column_stack([local[c['criterion_id']] for c in crit])
        glob = local_matrix @ weights

        print('\nГлобальные приоритеты:')
        order = np.argsort(-glob)
        for rank, idx in enumerate(order, start=1):
            b = allowed[idx]
            print(f'  #{rank} {b["book_id"]} {b["title"]}: {glob[idx]:.4f}')

        conn.execute('DELETE FROM recommendations')
        for rank, idx in enumerate(order, start=1):
            b = allowed[idx]
            conn.execute("""
                INSERT INTO recommendations
                (book_id, k1, k2, k3, k4, k5, global_priority, rank)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                b['book_id'],
                float(scores[idx, 0]), float(scores[idx, 1]), float(scores[idx, 2]),
                float(scores[idx, 3]), float(scores[idx, 4]),
                float(glob[idx]), rank,
            ))
        conn.commit()
        print(f'\nЗаписано {len(allowed)} рекомендаций в БД.')
        best = allowed[int(order[0])]
        print(f'Лучшая: {best["book_id"]} — {best["title"]}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
