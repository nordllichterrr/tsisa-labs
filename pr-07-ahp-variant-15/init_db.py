import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'books.db'

SCHEMA = """
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS criteria;
DROP TABLE IF EXISTS book_formats;
DROP TABLE IF EXISTS formats;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS disciplines;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    student_id   INTEGER PRIMARY KEY,
    full_name    TEXT NOT NULL,
    course       INTEGER NOT NULL,
    vark_dominant TEXT NOT NULL,
    goal         TEXT NOT NULL
);

CREATE TABLE disciplines (
    discipline_id INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    is_it         INTEGER NOT NULL CHECK (is_it IN (0,1)),
    is_mandatory  INTEGER NOT NULL CHECK (is_mandatory IN (0,1))
);

CREATE TABLE formats (
    format_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE
);

CREATE TABLE books (
    book_id       TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    author        TEXT,
    book_type     TEXT NOT NULL CHECK (book_type IN ('учебник','практикум','монография','методичка')),
    year          INTEGER NOT NULL,
    pages         INTEGER NOT NULL,
    complexity    REAL NOT NULL CHECK (complexity BETWEEN 0 AND 1),
    umo           INTEGER NOT NULL CHECK (umo IN (0,1)),
    ebs           INTEGER NOT NULL CHECK (ebs IN (0,1)),
    has_practice  INTEGER NOT NULL CHECK (has_practice IN (0,1)),
    discipline_id INTEGER REFERENCES disciplines(discipline_id)
);

CREATE TABLE book_formats (
    book_id   TEXT NOT NULL REFERENCES books(book_id),
    format_id INTEGER NOT NULL REFERENCES formats(format_id),
    PRIMARY KEY (book_id, format_id)
);

CREATE TABLE criteria (
    criterion_id  TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    direction     TEXT NOT NULL CHECK (direction IN ('max','min')),
    weight        REAL NOT NULL
);

CREATE TABLE recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        TEXT NOT NULL REFERENCES books(book_id),
    k1 REAL, k2 REAL, k3 REAL, k4 REAL, k5 REAL,
    global_priority REAL NOT NULL,
    rank            INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

STUDENT = (1, 'Лемдясова Екатерина Андреевна', 2, 'VISUAL', 'экзамен')

DISCIPLINES = [
    (1, 'Python для анализа данных', 1, 1),
]

FORMATS = [
    (1, 'VISUAL'), (2, 'AURAL'), (3, 'TEXT'), (4, 'INTERACTIVE'),
]

BOOKS = [
    ('A1', 'Python для анализа данных', 'Иванов И.И.', 'учебник', 2023, 480, 0.60, 1, 1, 1, 1),
    ('A2', 'Python: задачи и решения', 'Петров П.П.', 'практикум', 2021, 320, 0.50, 1, 1, 1, 1),
    ('A3', 'Data Science: теория', 'Сидоров С.С.', 'монография', 2019, 600, 0.90, 0, 1, 0, 1),
    ('A4', 'Анализ данных на Python. Практикум', 'Кузнецов К.К.', 'практикум', 2022, 400, 0.55, 1, 1, 1, 1),
    ('A5', 'Введение в машинное обучение', 'Смирнов С.С.', 'учебник', 2020, 520, 0.70, 1, 1, 0, 1),
]

BOOK_FORMATS = [
    ('A1', 1), ('A1', 3),
    ('A2', 3), ('A2', 4),
    ('A3', 3),
    ('A4', 3), ('A4', 4), ('A4', 1),
    ('A5', 1), ('A5', 3),
]

CRITERIA = [
    ('K1', 'Соответствие стилю VARK', 'max', 0.35),
    ('K2', 'Соответствие цели изучения', 'max', 0.25),
    ('K3', 'Новизна издания', 'max', 0.15),
    ('K4', 'Соответствие ФГОС', 'max', 0.15),
    ('K5', 'Трудозатраты на чтение', 'max', 0.10),
]


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.execute('INSERT INTO students VALUES (?,?,?,?,?)', STUDENT)
        conn.executemany('INSERT INTO disciplines VALUES (?,?,?,?)', DISCIPLINES)
        conn.executemany('INSERT INTO formats VALUES (?,?)', FORMATS)
        conn.executemany(
            'INSERT INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?)', BOOKS
        )
        conn.executemany('INSERT INTO book_formats VALUES (?,?)', BOOK_FORMATS)
        conn.executemany('INSERT INTO criteria VALUES (?,?,?,?)', CRITERIA)
        conn.commit()
    finally:
        conn.close()
    print(f'База создана: {DB_PATH}')
    print(f'  books: {len(BOOKS)}')
    print(f'  criteria: {len(CRITERIA)}')


if __name__ == '__main__':
    main()
