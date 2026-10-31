import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'books.db'


def get_param(conn: sqlite3.Connection, key: str) -> float:
    row = conn.execute('SELECT value FROM params WHERE param_key=?', (key,)).fetchone()
    if row is None:
        raise KeyError(f'Параметр {key} не найден')
    return row[0]


def apply_evaluations(conn: sqlite3.Connection) -> int:
    delta = get_param(conn, 'Delta')
    rows = conn.execute(
        'SELECT book_id, liked, disliked, clicked FROM evaluations'
    ).fetchall()
    for book_id, liked, disliked, clicked in rows:
        d = 0.0
        if clicked:
            d += delta
        if liked:
            d += 2 * delta
        if disliked:
            d -= 2 * delta
        conn.execute(
            'UPDATE books SET rating = MAX(0, MIN(1, rating + ?)) WHERE book_id=?',
            (d, book_id),
        )
    return len(rows)


def apply_precedents(conn: sqlite3.Connection) -> int:
    delta = get_param(conn, 'Delta')
    rows = conn.execute(
        'SELECT book_id, semester_result FROM precedents'
    ).fetchall()
    for book_id, result in rows:
        current = conn.execute(
            'SELECT rating FROM books WHERE book_id=?', (book_id,)
        ).fetchone()[0]
        new_r = max(0.0, min(1.0, current + delta * result))
        conn.execute('UPDATE books SET rating=? WHERE book_id=?', (new_r, book_id))
    return len(rows)


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f'Нет базы {DB_PATH}. Сначала запусти init_db.py')

    conn = sqlite3.connect(DB_PATH)
    try:
        print('=== До обработки обратной связи ===')
        for book_id, rating in conn.execute(
            'SELECT book_id, rating FROM books ORDER BY book_id'
        ):
            print(f'  {book_id}: {rating:.3f}')

        n_eval = apply_evaluations(conn)
        n_prec = apply_precedents(conn)
        conn.commit()

        print(f'\nПрименено оценок: {n_eval}, прецедентов: {n_prec}')

        print('\n=== После обработки ===')
        for book_id, rating in conn.execute(
            'SELECT book_id, rating FROM books ORDER BY book_id'
        ):
            print(f'  {book_id}: {rating:.3f}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
