# tools.py - LangChain Tools для фитнес-бота

import re
from typing import Optional, Dict, Any
from langchain.tools import tool

from agent import call_ai
from database import (
    create_user_if_not_exists,
    get_user_data,
    get_today_calories,
    save_user_weight,
    save_meal_entry,
    save_goal,
)

# -------------------- In-memory pending --------------------
PENDING: dict[int, dict] = {}


# -------------------- Утилиты --------------------

def _extract_qty(text: str) -> dict:
    """Извлекает количество (г/мл/шт) из текста."""
    t = (text or "").lower()
    grams = None
    ml = None
    pcs = None

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм)\b", t)
    if m:
        grams = float(m.group(1).replace(",", "."))

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:мл|миллилитр[а-я]*)\b", t)
    if m:
        ml = float(m.group(1).replace(",", "."))

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:шт|штук|кус(?:ок|ка)|яйц[ао]?)\b", t)
    if m:
        pcs = float(m.group(1).replace(",", "."))

    # словесные числа для яиц
    words = {"одно":1,"один":1,"одна":1,"две":2,"два":2,"три":3,"четыре":4,"пять":5,
             "шесть":6,"семь":7,"восемь":8,"девять":9,"десять":10}
    for w, n in words.items():
        if re.search(rf"\b{w}\b.*\bяйц", t):
            pcs = float(n)
            break

    return {"grams": grams, "ml": ml, "pcs": pcs}


# -------------------- AI-оценка калорий --------------------

def ai_estimate_calories(user_id: int, meal_description: str) -> Optional[int]:
    """
    Просим LLM вернуть одно целое число (ккал). Учитывает г/мл/шт. Фильтрует нереалистичные ответы.
    """
    q = _extract_qty(meal_description)
    system = (
        "Ты нутрициолог и калькулятор калорий. Верни только одно целое число — общие килокалории блюда.\n"
        "Если блюдо низкокалорийное (овощи, несладкие фрукты, вода/чай/кофе без сахара), не превышай 50 ккал/100 г.\n"
        "Сладости/масла/орехи/жареное/хлеб обычно 250–700 ккал/100 г.\n"
        "Если данных мало — оцени реалистично. Ответ — одно целое число без слов."
    )
    user = (
        f"Блюдо: {meal_description}\n"
        f"Количество: граммы={q.get('grams')}, мл={q.get('ml')}, штуки={q.get('pcs')}\n"
        "Ответ: одно целое число (ккал)."
    )
    try:
        print(f"[AI-KCAL→] uid={user_id} {meal_description}")
        resp = call_ai(user_id, user, system=system, temperature=0)
        txt = (resp or {}).get("response", "") if isinstance(resp, dict) else str(resp)
        print(f"[AI-KCAL←] {txt}")

        m = re.search(r"(-?\d+)", txt)
        if not m:
            return None
        val = int(m.group(1))

        # мягкие границы
        if val < 5:
            val = 5
        if val > 1200:
            val = 1200
        return val

    except Exception as e:
        print(f"[AI-KCAL ERR] {e}")
        return None


# ==================== LangChain Tools ====================

@tool
def log_meal_tool(user_id: int, description: str) -> str:
    """
    Логирует приём пищи пользователя. Автоматически оценивает калории через AI.
    
    Args:
        user_id: ID пользователя в Telegram
        description: Описание еды (например: "2 яйца", "борщ 300 мл", "халва 40 г")
    
    Returns:
        Сообщение с подтверждением и статистикой калорий за день
    """
    return log_meal(user_id, description)

@tool  
def get_remaining_calories_tool(user_id: int) -> str:
    """
    Показывает остаток калорий на сегодня для пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Статистику потребленных и оставшихся калорий
    """
    return get_remaining_calories(user_id)

@tool
def log_weight_tool(user_id: int, weight: float) -> str:
    """
    Сохраняет вес пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        weight: Вес в килограммах
        
    Returns:
        Подтверждение сохранения веса
    """
    return log_weight_entry(user_id, weight)

@tool
def create_plan_tool(user_id: int, goal_text: str) -> str:
    """
    Создает план похудения с целевым весом. Показывает превью плана для подтверждения.
    
    Args:
        user_id: ID пользователя в Telegram
        goal_text: Описание цели (например: "цель 75", "на 10 кг за 12 недель", "похудеть на 7 кг за 2 месяца")
        
    Returns:
        Превью плана питания с калориями и макросами
    """
    return create_weight_loss_plan(user_id, goal_text)

@tool
def generate_workout_tool(user_id: int, preferences: str = "") -> str:
    """
    Генерирует персональную программу тренировки.
    
    Args:
        user_id: ID пользователя в Telegram
        preferences: Предпочтения (например: "60 минут", "кардио", "для начинающих")
        
    Returns:
        План тренировки с разминкой, основной частью и заминкой
    """
    return generate_workout(user_id, preferences)

@tool
def show_progress_tool(user_id: int) -> str:
    """
    Показывает прогресс пользователя по весу.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Информацию о текущем весе и прогрессе
    """
    return analyze_progress(user_id)

@tool
def show_weight_tool(user_id: int) -> str:
    """
    Показывает текущий вес пользователя из профиля.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Текущий вес пользователя
    """
    return show_current_weight(user_id)

@tool
def show_goal_tool(user_id: int) -> str:
    """
    Показывает текущую цель по калориям пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Текущая дневная цель по калориям
    """
    return show_current_goal(user_id)


# ==================== Основные функции (без изменений) ====================

def log_meal(user_id: int, description: str, assistant_hint: str = "", meal_type: str = "generic") -> str:
    """Логирует приём пищи, калории считает AI."""
    create_user_if_not_exists(user_id)
    clean = (description or "").strip().lower()

    kcals = ai_estimate_calories(user_id, clean)
    if kcals is None:
        kcals = 150  # фолбэк

    save_meal_entry(user_id, clean, kcals)

    data = get_user_data(user_id) or {}
    goal = int(data.get("goal_calories") or 2000)
    eaten = int(get_today_calories(user_id) or 0)
    remaining = max(goal - eaten, 0)

    return (
        f"✅ Сохранено: {clean}\n"
        f"📊 Калории: ~{kcals} ккал\n"
        f"📈 Сегодня: ~{eaten}/{goal} ккал. Остаток: ~{remaining} ккал"
    )

def get_remaining_calories(user_id: int) -> str:
    data = get_user_data(user_id) or {}
    goal = int(data.get("goal_calories") or 2000)
    eaten = int(get_today_calories(user_id) or 0)
    remaining = max(goal - eaten, 0)
    used_pct = int(eaten / goal * 100) if goal else 0
    return (
        f"📊 Сегодня потреблено: ~{eaten} ккал\n"
        f"📈 Остаток: ~{remaining} ккал из {goal}\n"
        f"💯 Использовано: {used_pct}%"
    )


# -------------------- Вес / Прогресс --------------------

def update_weight(user_id: int, text: str) -> str:
    nums = re.findall(r"\d+(?:[.,]\d+)?", text or "")
    if not nums:
        return "Не вижу числа веса."
    w = float(nums[0].replace(",", "."))
    save_user_weight(user_id, w)
    return f"💾 Вес сохранён: {w:.1f} кг"

def log_weight_entry(user_id: int, weight: float) -> str:
    """Совместимость: сохранить вес по числу."""
    try:
        w = float(str(weight).replace(",", "."))
    except Exception:
        return "Не смог распознать вес."
    save_user_weight(user_id, w)
    return f"💾 Вес сохранён: {w:.1f} кг"

def analyze_progress(user_id: int) -> str:
    data = get_user_data(user_id) or {}
    w = data.get("weight")
    if w is None:
        return "Пока нет данных по прогрессу."
    return f"Текущий вес: {float(w):.1f} кг"

def show_current_weight(user_id: int) -> str:
    data = get_user_data(user_id) or {}
    w = data.get("weight")
    if w is None:
        return "Пока не знаю. Отправь: «взвесился 88»."
    return f"Текущий вес в профиле: {float(w):.1f} кг"

def show_current_goal(user_id: int) -> str:
    data = get_user_data(user_id) or {}
    goal_cals = int(data.get("goal_calories") or 0)
    if goal_cals <= 0:
        return "Цель пока не установлена."
    return f"Текущий дневной калораж: {goal_cals} ккал/день"


# -------------------- План / Цель --------------------

def _word_to_int_ru(word: str) -> Optional[int]:
    m = {
        "один": 1, "одна": 1, "одно": 1,
        "два": 2, "две": 2,
        "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
        "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
        "двенадцать": 12,
    }
    return m.get((word or "").strip().lower())

def _extract_plan_request(text: str, current: float) -> dict:
    """Понимает: «цель 75», «на 7 кг», «за 12 недель/3 месяца», «1 кг в неделю»."""
    t = (text or "").lower()

    # скорость (кг/нед)
    speed_kg_week = None
    m_speed = re.search(r"(\d+(?:[.,]\d+)?)\s*кг[^а-я0-9]{0,5}в[^а-я0-9]{0,5}нед", t)
    if m_speed:
        speed_kg_week = float(m_speed.group(1).replace(",", "."))

    # срок
    weeks_hint = None
    m_weeks = re.search(r"за\s*(\d+)\s*нед", t)
    if m_weeks:
        weeks_hint = int(m_weeks.group(1))
    m_months_word = re.search(r"за\s*([А-Яа-я]+)\s*месяц", t)
    if weeks_hint is None and m_months_word:
        w = _word_to_int_ru(m_months_word.group(1))
        if w:
            weeks_hint = w * 4
    m_months_num = re.search(r"за\s*(\d+)\s*месяц", t)
    if weeks_hint is None and m_months_num:
        weeks_hint = int(m_months_num.group(1)) * 4

    # абсолютная цель
    goal_abs = None
    if "цель" in t:
        m_abs = re.search(r"цель[^0-9]*(\d+(?:[.,]\d+)?)", t)
        if m_abs:
            goal_abs = float(m_abs.group(1).replace(",", "."))
    if goal_abs is None:
        m_abs2 = re.search(r"(?<!на\s)(\d+(?:[.,]\d+)?)\s*кг", t)
        if m_abs2 and "на " not in t:
            goal_abs = float(m_abs2.group(1).replace(",", "."))

    # относительная цель «на X кг»
    goal_rel = None
    m_rel = re.search(r"на\s*(\d+(?:[.,]\d+)?)\s*кг", t)
    if m_rel:
        goal_rel = float(m_rel.group(1).replace(",", "."))

    # итоговая цель
    if goal_abs is not None:
        goal = goal_abs
    elif goal_rel is not None:
        goal = max(40.0, float(current) - goal_rel)
    else:
        goal = None

    return {"goal": goal, "weeks_hint": weeks_hint, "speed_kg_week": speed_kg_week}

def _calc_simple_plan(current: float, goal: float, weeks_hint: Optional[int] = None,
                      height_cm: Optional[float] = None, age: Optional[int] = None,
                      activity_factor: float = 1.5) -> Dict[str, Any]:
    """
    Mifflin–St Jeor, ограниченный дефицит, безопасный минимум.
    """
    delta = float(current) - float(goal)
    if delta <= 0:
        weeks = 4
    else:
        weeks = max(1, weeks_hint) if weeks_hint else max(4, int(round(delta / 0.75)))

    h = float(height_cm) if height_cm else 175.0
    a = int(age) if age else 35
    bmr = 10 * float(current) + 6.25 * h - 5 * a + 5
    tdee = bmr * float(activity_factor)

    daily_deficit = (delta / weeks) * 7700.0 / 7.0 if weeks > 0 else 500.0
    daily_deficit = min(daily_deficit, 1000.0)
    daily_cal = int(round(tdee - daily_deficit))

    MIN_KCAL = 1500 if current >= 75 else 1300
    adjusted = False
    if daily_cal < MIN_KCAL and delta > 0:
        adjusted = True
        max_deficit_safe = max(tdee - MIN_KCAL, 300)
        kg_per_week_safe = max_deficit_safe * 7.0 / 7700.0
        if kg_per_week_safe <= 0:
            kg_per_week_safe = 0.3
        weeks = int(max(4, round(delta / kg_per_week_safe)))
        daily_deficit = min((delta / weeks) * 7700.0 / 7.0, 1000.0)
        daily_cal = int(round(max(MIN_KCAL, tdee - daily_deficit)))

    protein = int(round(float(goal) * 2.0))   # 2 г/кг
    fats    = int(round(float(goal) * 0.7))   # 0.7 г/кг
    kc_pf   = protein * 4 + fats * 9
    carbs   = max(int((daily_cal - kc_pf) / 4), 0)

    return {
        "daily_calories": daily_cal,
        "protein": protein,
        "carbs": carbs,
        "fats": fats,
        "weeks": weeks,
        "delta": float(delta),
        "tdee": int(round(tdee)),
        "adjusted": adjusted,
        "min_kcal": MIN_KCAL
    }

def create_weight_loss_plan(user_id: int, text: str = "") -> str:
    """
    Делаем детерминированный превью-план (без сохранения) и кладём в pending.
    Подтверждение — «да», отмена — «нет».
    """
    data = get_user_data(user_id) or {}
    current = float(data.get("weight") or 0)
    if current <= 0:
        return "Сначала пришли текущий вес: «взвесился 88»."

    parsed = _extract_plan_request(text, current)
    goal = parsed["goal"]
    if goal is None or goal >= current:
        return "Нужно указать цель ниже текущего веса. Пример: «цель 75» или «на 10 кг за 12 недель»."

    if parsed["weeks_hint"]:
        weeks = parsed["weeks_hint"]
    elif parsed["speed_kg_week"]:
        weeks = max(1, int(round((current - goal) / parsed["speed_kg_week"])))
    else:
        weeks = None

    plan = _calc_simple_plan(
        current=current,
        goal=goal,
        weeks_hint=weeks,
        height_cm=data.get("height"),
        age=data.get("age"),
        activity_factor=1.5
    )

    payload = {
        "target_weight": float(goal),
        "daily_calories": int(plan["daily_calories"]),
        "protein": int(plan["protein"]),
        "carbs": int(plan["carbs"]),
        "fats": int(plan["fats"]),
        "weeks": int(plan["weeks"]),
    }
    PENDING[user_id] = {"type": "plan", "payload": payload}

    safety = ""
    if plan["adjusted"]:
        safety = f"\n⚠️ Калораж увеличен до {plan['daily_calories']} ккал (минимум {plan['min_kcal']})."

    return (
        f"🎯 Цель: {goal:.1f} кг (текущий {current:.1f} кг)\n"
        f"🍽️ Калораж: ~{plan['daily_calories']} ккал/день (TDEE ~{plan['tdee']} ккал)\n"
        f"🥗 Макросы: белки {plan['protein']} г, углеводы {plan['carbs']} г, жиры {plan['fats']} г\n"
        f"⏰ Срок: ~{plan['weeks']} нед."
        f"{safety}\n\n"
        "Подходит? Напиши: «да» — применить, «нет» — отмена"
    )

def confirm_pending_action(user_id: int) -> str:
    p = PENDING.get(user_id)
    if not p or p.get("type") != "plan":
        return "Нет действий для подтверждения."
    d = p["payload"]

    save_goal(
        user_id,
        goal_text=f"Цель {d['target_weight']:.1f} кг",
        calories=int(d["daily_calories"]),
        proteins=int(d["protein"]),
        carbs=int(d["carbs"]),
        fats=int(d["fats"]),
        weeks=int(d["weeks"]),
    )
    PENDING.pop(user_id, None)
    return (
        "✅ План применён!\n\n"
        f"🎯 Цель: {float(d['target_weight']):.1f} кг\n"
        f"🍽️ Калораж: ~{int(d['daily_calories'])} ккал/день\n"
        f"🥗 Макросы: белки {int(d['protein'])} г, углеводы {int(d['carbs'])} г, жиры {int(d['fats'])} г\n"
        f"⏰ Срок: ~{int(d['weeks'])} нед."
    )

def cancel_pending_action(user_id: int) -> str:
    if PENDING.pop(user_id, None):
        return "❎ Отменено. Ничего не сохранено."
    return "Отменять нечего."


# -------------------- Тренировки / Болтовня --------------------

def generate_workout(user_id: int, text: str = "") -> str:
    """Генерация тренировки через LLM."""
    t = (text or "").lower()
    duration = 45
    for d in [90, 75, 60, 45, 30]:
        if re.search(rf"(^|\D){d}(\D|$)", t):
            duration = d
            break

    level = "начинающий"
    if "средн" in t:
        level = "средний"
    elif "продвинут" in t or "опыт" in t:
        level = "продвинутый"

    goal = "общая физическая форма"
    if "похуд" in t:
        goal = "похудение"
    elif "сила" in t:
        goal = "набор силы"
    elif "кардио" in t:
        goal = "кардио"

    system = "Ты тренер. Дай чёткий план тренировки: Разминка/Основная часть/Заминка. Коротко, пунктами, без Markdown."
    user = f"Составь тренировку на {duration} минут. Уровень: {level}. Цель: {goal}."
    try:
        resp = call_ai(user_id, user, system=system, temperature=0.2)
        txt = (resp or {}).get("response", "") if isinstance(resp, dict) else str(resp)
        return txt.strip() or _fallback_workout()
    except Exception:
        return _fallback_workout()

def _fallback_workout() -> str:
    return (
        "Разминка (5 мин): махи руками, круговые плечами, лёгкие приседания\n"
        "Основная (35 мин): приседания 4×12, отжимания 4×10, планка 3×40с, выпады 3×10/н, пресс 3×15\n"
        "Заминка (5 мин): растяжка ног и спины"
    )

def small_talk(user_id: int, text: str) -> str:
    """Свободный ответ через LLM."""
    try:
        resp = call_ai(user_id, text, system="Отвечай кратко и по делу.", temperature=0.3)
        msg = (resp or {}).get("response", "").strip()
        return msg if msg else "Попробуй: «цель 75», «взвесился 88», «я съел 2 яйца»."
    except Exception:
        return "Попробуй: «цель 75», «взвесился 88», «я съел 2 яйца»."


# -------------------- Совместимость со старыми именами --------------------

def propose_weight_loss_plan(user_id: int, text: str = "") -> str:
    """Старое имя → перенаправление."""
    return create_weight_loss_plan(user_id, text)

def propose_plan(user_id: int, text: str = "") -> str:
    """Аналог старого имени."""
    return create_weight_loss_plan(user_id, text)


# ==================== Список всех LangChain tools для агента ====================

def get_all_tools():
    """Возвращает список всех LangChain tools для использования в агенте"""
    return [
        log_meal_tool,
        get_remaining_calories_tool,
        log_weight_tool,
        create_plan_tool,
        generate_workout_tool,
        show_progress_tool,
        show_weight_tool,
        show_goal_tool,
    ]