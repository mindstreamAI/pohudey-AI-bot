import json

ALLOWED_TOOLS = {
    "log_meal",
    "get_remaining_calories",
    "log_weight",
    "create_plan",
    "workout",
    "progress",
    "show_weight",
    "chat",
}

def parse_tool_call(text: str):
    """
    Ожидается строгий JSON:
    {"tool": "<one_of_allowed>", "data": "<string>", "response": "<string>"}
    При любой ошибке — фоллбек ("chat", "", <raw_text>).
    """
    try:
        obj = json.loads(text or "")
        if not isinstance(obj, dict):
            raise ValueError("not a dict")

        tool = obj.get("tool")
        data = obj.get("data", "")
        resp = obj.get("response", "")

        if tool not in ALLOWED_TOOLS:
            raise ValueError("unknown tool")
        if not isinstance(data, str) or not isinstance(resp, str):
            raise ValueError("bad fields")

        return tool, data, resp
    except Exception:
        # Фоллбек: обычный ответ чатом
        return "chat", "", (text or "").strip()
