def calc_daily_target(user: dict | None) -> int:
    """
    Грубая оценка дневного калоража (BMR Миффлин + активность 1.3 − дефицит 500).
    Если нет веса/роста/возраста — используем безопасные значения.
    """
    if not user:
        weight, height, age = 80.0, 175.0, 35.0
    else:
        weight = float(user.get("weight") or 80.0)
        height = 175.0  # у нас в users нет роста/возраста — подставляем разумные дефолты
        age = 35.0
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
    tdee = int(bmr * 1.3)
    return max(tdee - 500, 1200)
