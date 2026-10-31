import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'books.db'
RNG = random.Random(42)
N_STUDENTS = 150

SCHEMA = """
DROP TABLE IF EXISTS precedents;
DROP TABLE IF EXISTS teacher_decisions;
DROP TABLE IF EXISTS evaluations;
DROP TABLE IF EXISTS recommendations;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS params;
DROP TABLE IF EXISTS criteria;
DROP TABLE IF EXISTS book_formats;
DROP TABLE IF EXISTS formats;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS disciplines;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    student_id    INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    course        INTEGER NOT NULL,
    vark_dominant TEXT NOT NULL,
    goal          TEXT NOT NULL
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
    rating        REAL NOT NULL DEFAULT 0.6,
    discipline_id INTEGER REFERENCES disciplines(discipline_id)
);

CREATE TABLE book_formats (
    book_id   TEXT NOT NULL REFERENCES books(book_id),
    format_id INTEGER NOT NULL REFERENCES formats(format_id),
    PRIMARY KEY (book_id, format_id)
);

CREATE TABLE criteria (
    criterion_id TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    direction    TEXT NOT NULL CHECK (direction IN ('max','min')),
    weight       REAL NOT NULL
);

CREATE TABLE recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         TEXT NOT NULL REFERENCES books(book_id),
    student_id      INTEGER REFERENCES students(student_id),
    k1 REAL, k2 REAL, k3 REAL, k4 REAL, k5 REAL,
    global_priority REAL NOT NULL,
    rank            INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evaluations (
    evaluation_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id          TEXT NOT NULL REFERENCES books(book_id),
    student_id       INTEGER NOT NULL REFERENCES students(student_id),
    liked            INTEGER NOT NULL DEFAULT 0 CHECK (liked IN (0,1)),
    disliked         INTEGER NOT NULL DEFAULT 0 CHECK (disliked IN (0,1)),
    clicked          INTEGER NOT NULL DEFAULT 0 CHECK (clicked IN (0,1)),
    list_viewed      INTEGER NOT NULL DEFAULT 0 CHECK (list_viewed IN (0,1)),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teacher_decisions (
    decision_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id          TEXT NOT NULL REFERENCES books(book_id),
    approved         INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0,1)),
    edited           INTEGER NOT NULL DEFAULT 0 CHECK (edited IN (0,1)),
    new_year_limit   INTEGER,
    sent_to_process  INTEGER NOT NULL DEFAULT 0 CHECK (sent_to_process IN (0,1)),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE precedents (
    precedent_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         TEXT NOT NULL REFERENCES books(book_id),
    semester_result REAL NOT NULL CHECK (semester_result BETWEEN 0 AND 1),
    reused          INTEGER NOT NULL DEFAULT 0 CHECK (reused IN (0,1)),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rules (
    rule_id        TEXT PRIMARY KEY,
    rule_type      INTEGER NOT NULL CHECK (rule_type BETWEEN 1 AND 6),
    condition_text TEXT NOT NULL,
    action_text    TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE TABLE params (
    param_key TEXT PRIMARY KEY,
    value     REAL NOT NULL,
    meaning   TEXT
);

CREATE INDEX idx_eval_student ON evaluations(student_id);
CREATE INDEX idx_eval_book ON evaluations(book_id);
CREATE INDEX idx_rec_student ON recommendations(student_id);
"""

DISCIPLINES = [
    (1, 'Python для анализа данных', 1, 1),
    (2, 'Базы данных', 1, 1),
]

FORMATS = [(1, 'VISUAL'), (2, 'AURAL'), (3, 'TEXT'), (4, 'INTERACTIVE')]

BOOKS = [
    ('A1', 'Python для анализа данных', 'Иванов И.И.', 'учебник', 2023, 480, 0.60, 1, 1, 1, 0.70, 1),
    ('A2', 'Python: задачи и решения', 'Петров П.П.', 'практикум', 2021, 320, 0.50, 1, 1, 1, 0.65, 1),
    ('A3', 'Data Science: теория', 'Сидоров С.С.', 'монография', 2019, 600, 0.90, 0, 1, 0, 0.40, 1),
    ('A4', 'Анализ данных на Python. Практикум', 'Кузнецов К.К.', 'практикум', 2022, 400, 0.55, 1, 1, 1, 0.75, 1),
    ('A5', 'Введение в машинное обучение', 'Смирнов С.С.', 'учебник', 2020, 520, 0.70, 1, 1, 0, 0.55, 1),
    ('B1', 'SQL: полное руководство', 'Грофф Дж.', 'учебник', 2022, 640, 0.65, 1, 1, 1, 0.80, 2),
    ('B2', 'PostgreSQL изнутри', 'Рогов Е.В.', 'монография', 2020, 700, 0.85, 0, 1, 0, 0.50, 2),
    ('B3', 'Практикум по SQL', 'Белов В.В.', 'практикум', 2023, 350, 0.55, 1, 1, 1, 0.70, 2),
]

BOOK_FORMATS = [
    ('A1', 1), ('A1', 3),
    ('A2', 3), ('A2', 4),
    ('A3', 3),
    ('A4', 3), ('A4', 4), ('A4', 1),
    ('A5', 1), ('A5', 3),
    ('B1', 1), ('B1', 3), ('B1', 4),
    ('B2', 3),
    ('B3', 3), ('B3', 4),
]

CRITERIA = [
    ('K1', 'Соответствие стилю VARK', 'max', 0.35),
    ('K2', 'Соответствие цели изучения', 'max', 0.25),
    ('K3', 'Новизна издания', 'max', 0.15),
    ('K4', 'Соответствие ФГОС', 'max', 0.15),
    ('K5', 'Трудозатраты на чтение', 'max', 0.10),
]

RULES = [
    ('1.1', 1, 'V_max >= V_min', 'S_mix = 0; F_prior = формат по T'),
    ('1.2', 1, 'V_max < V_min', 'S_mix = 1'),
    ('1.3', 1, 'S_mix=1 & T1=Visual & T2=Aural', 'F_prior = комб. VISUAL+AURAL'),
    ('2.1', 2, 'Av = 0', 'Accept = 0'),
    ('2.2', 2, 'T_type in (3,4)', 'Accept = 0'),
    ('2.3', 2, 'Y_cur - Y > Y_max & дисциплина=IT', 'Accept = 0'),
    ('2.4', 2, 'G = 0 & дисциплина обязательная', 'Accept = 0'),
    ('3.1', 3, 'Accept=1 & K1>=0.7 & K2>=0.7', 'книга в топ-10'),
    ('3.2', 3, 'K4 >= 0.8', 'книга в обязательном списке'),
    ('3.3', 3, 'объём > Length_max', 'книга помечается как дополнительная'),
    ('3.4', 3, 'R_book < R_min', 'книга не попадает в топ-10'),
    ('3.5', 3, 'цель=экзамен & есть практические задания', 'K2 := K2 + 0.2'),
    ('4.1', 4, 'C<=C_max & L<=L_max', 'Est_score = 2'),
    ('4.2', 4, 'C>C_max | L>L_max', 'Est_score = 1'),
    ('4.3', 4, 'мало времени & L>200', 'Est_score = 0'),
    ('4.4', 4, 'Read_hours > 10', 'Est_score := max(Est_score-1,0)'),
    ('5.1', 5, 'S_click = 1', 'R_book := R_book + Delta'),
    ('5.2', 5, 'S_like = 1', 'R_book := R_book + 2*Delta'),
    ('5.3', 5, 'S_dislike = 1', 'R_book := R_book - 2*Delta'),
    ('5.4', 5, 'S_click=0 & S_like=0 & список просмотрен', 'Req_re = 1'),
    ('5.5', 5, 'Req_re = 1', 'K1 := 0.5'),
    ('6.1', 6, 'P_edit=1 & критерий="только новые"', 'Year_max_new = 3'),
    ('6.2', 6, 'P_approve = 1', 'Final=1; список в учебный процесс'),
    ('6.3', 6, 'P_approve = 0', 'Req_re = 1'),
    ('6.4', 6, 'Result_sem >= 0.8', 'R_avg := R_avg + Delta'),
    ('6.5', 6, 'Result_sem < 0.5', 'R_avg := R_avg - Delta'),
    ('6.6', 6, 'R_new = R_avg + Delta*Result_sem', 'пересчёт рейтинга'),
]

PARAMS = [
    ('V_min', 0.5, 'Минимальный вес доминирующего канала'),
    ('Y_max', 5.0, 'Макс. возраст издания для IT-дисциплин (лет)'),
    ('R_min', 0.6, 'Минимальный рейтинг книги в БЗ'),
    ('Length_max', 500.0, 'Предельный объём книги, стр.'),
    ('C_max', 0.8, 'Порог сложности для студента'),
    ('Delta', 0.1, 'Шаг изменения рейтинга'),
    ('w_K1', 0.35, 'Вес критерия K1'),
    ('w_K2', 0.25, 'Вес критерия K2'),
    ('w_K3', 0.15, 'Вес критерия K3'),
    ('w_K4', 0.15, 'Вес критерия K4'),
    ('w_K5', 0.10, 'Вес критерия K5'),
]

LAST_NAMES = [
    'Лемдясова', 'Иванов', 'Петрова', 'Сидоров', 'Кузнецов', 'Смирнов',
    'Белов', 'Рогов', 'Грофф', 'Морозов', 'Новиков', 'Волков',
    'Соколов', 'Лебедев', 'Козлов', 'Егоров', 'Павлов', 'Семёнов',
    'Голубев', 'Виноградов', 'Богданов', 'Воробьёв', 'Фёдоров', 'Михайлов',
    'Никитин', 'Орлов', 'Андреев', 'Макаров', 'Сергеев', 'Титов',
]
FIRST_NAMES_M = [
    'Алексей', 'Иван', 'Пётр', 'Николай', 'Сергей', 'Дмитрий',
    'Андрей', 'Михаил', 'Владимир', 'Олег', 'Павел', 'Артём',
    'Максим', 'Егор', 'Кирилл', 'Денис',
]
FIRST_NAMES_F = [
    'Екатерина', 'Мария', 'Анна', 'Ольга', 'Елена', 'Татьяна',
    'Наталья', 'Ирина', 'Светлана', 'Юлия', 'Ксения', 'Дарья',
    'Алиса', 'Полина', 'Вера', 'Софья',
]
MIDDLE_M = [
    'Алексеевич', 'Иванович', 'Петрович', 'Николаевич', 'Сергеевич',
    'Дмитриевич', 'Андреевич', 'Михайлович', 'Владимирович', 'Олегович',
]
MIDDLE_F = [
    'Алексеевна', 'Ивановна', 'Петровна', 'Николаевна', 'Сергеевна',
    'Дмитриевна', 'Андреевна', 'Михайловна', 'Владимировна', 'Олеговна',
]
VARK = ['VISUAL', 'AURAL', 'TEXT', 'INTERACTIVE']
GOALS = ['экзамен', 'курсовая', 'общее освоение']


def gen_students(n: int):
    rows = [(1, 'Лемдясова Екатерина Алексеевна', 2, 'VISUAL', 'экзамен')]
    used = {'Лемдясова Екатерина Алексеевна'}
    sid = 2
    while len(rows) < n:
        gender = RNG.choice(['M', 'F'])
        last = RNG.choice(LAST_NAMES)
        first = RNG.choice(FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F)
        middle = RNG.choice(MIDDLE_M if gender == 'M' else MIDDLE_F)
        full = f'{last} {first} {middle}'
        if full in used:
            continue
        used.add(full)
        rows.append((
            sid, full,
            RNG.choice([1, 2, 3, 4]),
            RNG.choice(VARK),
            RNG.choice(GOALS),
        ))
        sid += 1
    return rows


def gen_evaluations(students, books):
    rows = []
    for s in students:
        sid = s[0]
        n_books = RNG.randint(2, 5)
        picked = RNG.sample(books, k=min(n_books, len(books)))
        for b in picked:
            bid = b[0]
            clicked = RNG.randint(0, 1)
            liked = RNG.randint(0, 1) if clicked else RNG.randint(0, 1)
            disliked = 0 if liked else RNG.randint(0, 1)
            viewed = 1 if (clicked or liked) else RNG.randint(0, 1)
            rows.append((bid, sid, liked, disliked, clicked, viewed))
    return rows


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        students = gen_students(N_STUDENTS)
        conn.executemany('INSERT INTO students VALUES (?,?,?,?,?)', students)
        conn.executemany('INSERT INTO disciplines VALUES (?,?,?,?)', DISCIPLINES)
        conn.executemany('INSERT INTO formats VALUES (?,?)', FORMATS)
        conn.executemany('INSERT INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', BOOKS)
        conn.executemany('INSERT INTO book_formats VALUES (?,?)', BOOK_FORMATS)
        conn.executemany('INSERT INTO criteria VALUES (?,?,?,?)', CRITERIA)
        conn.executemany('INSERT INTO rules VALUES (?,?,?,?,?)',
                         [(rid, rt, cond, act, 1) for rid, rt, cond, act in RULES])
        conn.executemany('INSERT INTO params VALUES (?,?,?)', PARAMS)

        eval_rows = gen_evaluations(students, BOOKS)
        conn.executemany(
            'INSERT INTO evaluations '
            '(book_id, student_id, liked, disliked, clicked, list_viewed) '
            'VALUES (?,?,?,?,?,?)', eval_rows
        )

        decisions = [(b[0], 1, 0, None, 1) for b in BOOKS if b[3] in ('учебник', 'практикум')]
        decisions += [(b[0], 0, 0, None, 0) for b in BOOKS if b[3] == 'монография']
        conn.executemany(
            'INSERT INTO teacher_decisions '
            '(book_id, approved, edited, new_year_limit, sent_to_process) '
            'VALUES (?,?,?,?,?)', decisions
        )

        precedents = []
        for b in BOOKS:
            for _ in range(RNG.randint(3, 8)):
                precedents.append((
                    b[0],
                    round(RNG.uniform(0.3, 1.0), 3),
                    RNG.randint(0, 1),
                ))
        conn.executemany(
            'INSERT INTO precedents (book_id, semester_result, reused) '
            'VALUES (?,?,?)', precedents
        )

        conn.commit()
    finally:
        conn.close()

    print(f'База создана: {DB_PATH}')
    print(f'  students:          {len(students)}')
    print(f'  disciplines:       {len(DISCIPLINES)}')
    print(f'  formats:           {len(FORMATS)}')
    print(f'  books:             {len(BOOKS)}')
    print(f'  book_formats:      {len(BOOK_FORMATS)}')
    print(f'  criteria:          {len(CRITERIA)}')
    print(f'  rules:             {len(RULES)}')
    print(f'  params:            {len(PARAMS)}')
    print(f'  evaluations:       {len(eval_rows)}')
    print(f'  teacher_decisions: {len(decisions)}')
    print(f'  precedents:        {len(precedents)}')


if __name__ == '__main__':
    main()
