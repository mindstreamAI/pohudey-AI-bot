import sqlite3
from datetime import datetime

DB_PATH = "fitness.db"


# ---------- базовые функции ----------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            weight REAL,
            height REAL,
            goal_calories INTEGER DEFAULT 2000,
            created_at TEXT
        )
    """)

    # Вес
    c.execute("""
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weight REAL,
            created_at TEXT
        )
    """)

    # Приёмы пищи
    c.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            calories INTEGER,
            created_at TEXT
        )
    """)

    # Цели
    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal_text TEXT,
            calories INTEGER,
            proteins INTEGER,
            carbs INTEGER,
            fats INTEGER,
            weeks INTEGER,
            created_at TEXT
        )
    """)

    # Настройки (напоминания и др.)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            remind_weekly INTEGER DEFAULT 1,
            last_weighin_reminder_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✓ Инициализирую БД...")


# ---------- операции с пользователями ----------

def create_user_if_not_exists(user_id: int, name=None, age=None, weight=None, height=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = c.fetchone()
    if not exists:
        c.execute(
            "INSERT INTO users (user_id, name, age, weight, height, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, age, weight, height, datetime.now().isoformat())
        )
        # настройки по умолчанию
        c.execute("INSERT OR IGNORE INTO settings (user_id, remind_weekly, last_weighin_reminder_at) VALUES (?, 1, NULL)", (user_id,))
        conn.commit()
        print(f"[DB] created user {user_id}")
    else:
        # гарантируем наличие настроек
        c.execute("INSERT OR IGNORE INTO settings (user_id, remind_weekly, last_weighin_reminder_at) VALUES (?, 1, NULL)", (user_id,))
        conn.commit()
    conn.close()


def delete_user_by_id(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    for table in ["users", "weights", "meals", "goals", "settings"]:
        c.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    print(f"[DB] deleted user {user_id} and related data")


def get_user_data(user_id: int) -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name, age, weight, height, goal_calories FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    # калории за сегодня
    today_cals = get_today_calories(user_id)
    conn.close()
    if not row:
        return {}
    return {
        "name": row[0],
        "age": row[1],
        "weight": row[2],
        "height": row[3],
        "goal_calories": row[4],
        "calories_today": today_cals
    }


# ---------- вес ----------

def save_user_weight(user_id: int, weight: float):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO weights (user_id, weight, created_at) VALUES (?, ?, ?)",
              (user_id, weight, datetime.now().isoformat()))
    c.execute("UPDATE users SET weight=? WHERE user_id=?", (weight, user_id))
    conn.commit()
    conn.close()
    print(f"[DB] saved weight {weight} for {user_id}")


def get_last_weight_dt(user_id: int) -> str | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(created_at) FROM weights WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


# ---------- приёмы пищи ----------

def save_meal_entry(user_id: int, description: str, calories: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO meals (user_id, description, calories, created_at) VALUES (?, ?, ?, ?)",
        (user_id, description, calories, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"[DB] meal logged {description} ({calories} ккал) for {user_id}")


def get_today_calories(user_id: int) -> int:
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute(
        "SELECT SUM(calories) FROM meals WHERE user_id=? AND created_at LIKE ?",
        (user_id, f"{today}%")
    )
    res = c.fetchone()
    conn.close()
    return int(res[0] or 0)


# ---------- цели ----------

def save_goal(user_id: int, goal_text: str, calories: int, proteins: int, carbs: int, fats: int, weeks: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO goals (user_id, goal_text, calories, proteins, carbs, fats, weeks, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, goal_text, calories, proteins, carbs, fats, weeks, datetime.now().isoformat())
    )
    c.execute("UPDATE users SET goal_calories=? WHERE user_id=?", (calories, user_id))
    conn.commit()
    conn.close()
    print(f"[DB] saved goal for {user_id}: {goal_text}")


# ---------- напоминания раз в неделю ----------

def set_remind_weekly(user_id: int, enabled: bool):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO settings (user_id, remind_weekly, last_weighin_reminder_at) VALUES (?, ?, NULL)", (user_id, 1 if enabled else 0))
    c.execute("UPDATE settings SET remind_weekly=? WHERE user_id=?", (1 if enabled else 0, user_id))
    conn.commit()
    conn.close()
    print(f"[DB] remind_weekly set to {enabled} for {user_id}")

def update_last_weighin_reminder(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE settings SET last_weighin_reminder_at=? WHERE user_id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def list_users_for_weekly_reminder() -> list[int]:
    """
    Возвращает user_id, кому пора напомнить:
    - remind_weekly=1
    - нет веса никогда ИЛИ последний вес был ≥ 7 дней назад
    - и мы не слали напоминание за последние ~6.5 дней
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        WITH last_w AS (
            SELECT user_id, MAX(created_at) AS last_weight
            FROM weights
            GROUP BY user_id
        )
        SELECT s.user_id
        FROM settings s
        LEFT JOIN last_w w ON w.user_id = s.user_id
        WHERE s.remind_weekly = 1
          AND (
                w.last_weight IS NULL
                OR (julianday('now') - julianday(w.last_weight)) >= 7.0
              )
          AND (
                s.last_weighin_reminder_at IS NULL
                OR (julianday('now') - julianday(s.last_weighin_reminder_at)) >= 6.5
              )
    """)
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]
