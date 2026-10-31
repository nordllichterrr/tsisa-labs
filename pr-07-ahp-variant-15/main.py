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


def score_k1(formats: str, dominant: str) -> float:
    return 1.0 if dominant in set((formats or '').split('|')) else 0.2


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


def process_student(conn, student, allowed, crit, weights, r_min, lo, hi, max_load):
    scores = np.array([
        [
            score_k1(b['formats'], student['vark_dominant']),
            score_k2(b['has_practice'], student['goal']),
            score_k3(b['year'], lo, hi),
            score_k4(b),
            score_k5(b['pages'], b['complexity'], max_load),
        ]
        for b in allowed
    ])

    local = {}
    for i, c in enumerate(crit):
        m = build_pairwise(scores[:, i].tolist())
        pv, _ = priority_vector(m)
        local[c['criterion_id']] = pv
        
        for b_idx, b_item in enumerate(allowed):
            conn.execute(
                "INSERT INTO local_priorities (student_id, criterion_id, book_id, priority) VALUES (?, ?, ?, ?)",
                (student['student_id'], c['criterion_id'], b_item['book_id'], float(pv[b_idx]))
            )

    local_matrix = np.column_stack([local[c['criterion_id']] for c in crit])
    glob = local_matrix @ weights

    order = np.argsort(-glob)
    rank = 1
    rows = []
    for idx in order:
        b = allowed[idx]
        if b['rating'] < r_min:
            continue
        rows.append((
            b['book_id'], student['student_id'],
            float(scores[idx, 0]), float(scores[idx, 1]), float(scores[idx, 2]),
            float(scores[idx, 3]), float(scores[idx, 4]),
            float(glob[idx]), rank,
        ))
        rank += 1
    return rows


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f'Нет базы {DB_PATH}. Сначала запусти init_db.py')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        books = conn.execute("""
            SELECT b.*, GROUP_CONCAT(f.name, '|') AS formats
            FROM books b
            LEFT JOIN book_formats bf ON bf.book_id = b.book_id
            LEFT JOIN formats f ON f.format_id = bf.format_id
            WHERE b.discipline_id = 1
            GROUP BY b.book_id
        """).fetchall()
        
        allowed = [b for b in books
                   if b['ebs'] == 1 and b['book_type'] in ('учебник', 'практикум')]
        crit = conn.execute('SELECT * FROM criteria ORDER BY criterion_id').fetchall()
        
        # Считаем Q2 (веса критериев) и сохраняем в БД
        conn.execute('DELETE FROM criteria_weights')
        criteria_matrix = np.array([
            [1,    3,    5,    5,    7],
            [1/3,  1,    3,    3,    5],
            [1/5,  1/3,  1,    1,    3],
            [1/5,  1/3,  1,    1,    3],
            [1/7,  1/5,  1/3,  1/3,  1]
        ])
        q2_weights, _ = priority_vector(criteria_matrix)
        for i, c in enumerate(crit):
            conn.execute(
                "INSERT INTO criteria_weights (criterion_id, q2_weight) VALUES (?, ?)",
                (c['criterion_id'], float(q2_weights[i]))
            )

        weights = np.array([c['weight'] for c in crit])
        r_min = conn.execute(
            "SELECT value FROM params WHERE param_key='R_min'"
        ).fetchone()[0]

        lo = min(b['year'] for b in allowed)
        hi = max(b['year'] for b in allowed)
        max_load = max(b['pages'] * b['complexity'] for b in allowed)

        students = conn.execute('SELECT * FROM students ORDER BY student_id').fetchall()
        print(f'Студентов: {len(students)}')
        print(f'Допустимых книг: {len(allowed)} ({[b["book_id"] for b in allowed]})')

        conn.execute('DELETE FROM recommendations')
        conn.execute('DELETE FROM local_priorities')
        total = 0
        for s in students:
            rows = process_student(conn, s, allowed, crit, weights, r_min, lo, hi, max_load)
            conn.executemany("""
                INSERT INTO recommendations
                (book_id, student_id, k1, k2, k3, k4, k5, global_priority, rank)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, rows)
            total += len(rows)
        conn.commit()

        print(f'Записано рекомендаций: {total}')
        print(f'Записано локальных приоритетов: {conn.execute("SELECT COUNT(*) FROM local_priorities").fetchone()[0]}')
        print(f'Записано весов критериев: {conn.execute("SELECT COUNT(*) FROM criteria_weights").fetchone()[0]}')

        print('\nТоп-1 для первых 10 студентов:')
        for s in students[:10]:
            best = conn.execute("""
                SELECT book_id, global_priority FROM recommendations
                WHERE student_id=? ORDER BY rank LIMIT 1
            """, (s['student_id'],)).fetchone()
            print(f'  #{s["student_id"]} {s["full_name"]} '
                  f'({s["vark_dominant"]}/{s["goal"]}) -> '
                  f'{best[0]} ({best[1]:.4f})')

        print('\nПопулярность книг (сколько раз попали в топ-1):')
        for row in conn.execute("""
            SELECT book_id, COUNT(*) AS n
            FROM recommendations WHERE rank=1
            GROUP BY book_id ORDER BY n DESC
        """):
            print(f'  {row[0]}: {row[1]}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
