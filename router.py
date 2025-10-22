# router.py - LangChain Agent Router

import re
from typing import Dict
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from config import get_llm
from tools import (
    log_meal,
    get_remaining_calories,
    log_weight_entry,
    generate_workout,
    analyze_progress,
    small_talk,
    show_current_weight,
    show_current_goal,
    propose_weight_loss_plan,
    confirm_pending_action,
    cancel_pending_action,
    get_all_tools,
)

# ==================== Memory для каждого пользователя ====================
user_memories: Dict[int, ConversationBufferMemory] = {}

def get_or_create_memory(user_id: int) -> ConversationBufferMemory:
    """Получает или создает память для пользователя"""
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[user_id]


# ==================== LangChain Agent ====================

AGENT_PROMPT = """Ты фитнес-ассистент, который помогает пользователям с питанием, весом и тренировками.

У тебя есть следующие инструменты:
{tools}

Названия инструментов: {tool_names}

Используй следующий формат:

Question: входной вопрос, на который нужно ответить
Thought: всегда думай о том, что делать
Action: действие, должно быть одно из [{tool_names}]
Action Input: ввод для действия
Observation: результат действия
... (этот Thought/Action/Action Input/Observation может повторяться N раз)
Thought: теперь я знаю окончательный ответ
Final Answer: окончательный ответ на исходный входной вопрос

ВАЖНЫЕ ПРАВИЛА для распознавания:

ЗАПРОСЫ СОВЕТОВ (НЕ используй tools, отвечай сам):
- "дай пример завтрака/обеда/ужина", "посоветуй что поесть", "что можно съесть"
- "какой завтрак полезный", "идеи для перекуса", "варианты блюд"
- "что лучше съесть на", "что приготовить", "рецепт"
→ Просто дай совет своими словами, учитывая калораж пользователя

ЛОГИРОВАНИЕ ЕДЫ (используй log_meal):
- ТОЛЬКО если ЯВНО сказано: "я съел X", "я выпил X", "съел X", "позавтракал X"
- Утвердительная форма прошедшего времени: "ел X", "на завтрак было X"
→ Используй log_meal tool

Другие tools:
- Вес (взвесился X, вес X кг) → log_weight
- План/цель (цель X, похудеть на X) → create_plan
- Тренировка (создай/дай тренировку) → workout
- Остаток калорий (сколько осталось, остаток) → get_remaining_calories
- Прогресс (мой прогресс, как дела) → progress или show_weight

Начнем!

Question: {input}
Thought:{agent_scratchpad}"""

def create_fitness_agent(user_id: int) -> AgentExecutor:
    """Создает LangChain агента для конкретного пользователя"""
    llm = get_llm()
    tools = get_all_tools()
    
    # Оборачиваем tools чтобы передавать user_id автоматически
    def wrap_tool(tool_func, tool_name, tool_description):
        """Обертка для передачи user_id в tool"""
        from langchain.tools import Tool
        
        def wrapped_func(input_str: str) -> str:
            # Парсим вход - может быть просто строка или user_id + данные
            return tool_func(user_id, input_str)
        
        return Tool(
            name=tool_name,
            func=wrapped_func,
            description=tool_description
        )
    
    # Создаем обернутые tools с user_id
    from langchain.tools import Tool
    
    wrapped_tools = [
        Tool(
            name="log_meal",
            func=lambda desc: log_meal(user_id, desc),
            description="Логирует приём пищи. Вход: описание еды (например: '2 яйца', 'борщ 300 мл')"
        ),
        Tool(
            name="get_remaining_calories",
            func=lambda _: get_remaining_calories(user_id),
            description="Показывает остаток калорий на сегодня. Вход: пустая строка или любой текст"
        ),
        Tool(
            name="log_weight",
            func=lambda weight_str: log_weight_entry(user_id, float(re.search(r'\d+(?:[.,]\d+)?', weight_str).group().replace(',', '.')) if re.search(r'\d+(?:[.,]\d+)?', weight_str) else 0),
            description="Сохраняет вес пользователя. Вход: вес в кг (число)"
        ),
        Tool(
            name="create_plan",
            func=lambda goal_text: propose_weight_loss_plan(user_id, goal_text),
            description="Создает план похудения. Вход: описание цели ('цель 75', 'на 10 кг за 12 недель')"
        ),
        Tool(
            name="workout",
            func=lambda prefs: generate_workout(user_id, prefs),
            description="Генерирует тренировку. Вход: предпочтения ('60 минут', 'кардио', 'для начинающих')"
        ),
        Tool(
            name="progress",
            func=lambda _: analyze_progress(user_id),
            description="Показывает прогресс по весу. Вход: пустая строка"
        ),
        Tool(
            name="show_weight",
            func=lambda _: show_current_weight(user_id),
            description="Показывает текущий вес. Вход: пустая строка"
        ),
        Tool(
            name="show_goal",
            func=lambda _: show_current_goal(user_id),
            description="Показывает текущую цель по калориям. Вход: пустая строка"
        ),
    ]
    
    prompt = PromptTemplate.from_template(AGENT_PROMPT)
    
    agent = create_react_agent(llm, wrapped_tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=wrapped_tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )
    
    return agent_executor


# ==================== Основной роутер ====================

# Прямые триггеры команд (до агента)
INTENT_RULES = [
    ("трениров", "workout"),
    ("прогресс", "progress"),
    ("остаток", "get_remaining_calories"),
    ("мой вес", "show_weight"),
    ("вес?", "show_weight"),
    ("моя цель", "show_goal"),
    ("текущая цель", "show_goal"),
    ("я съел", "log_meal"),
    ("съел", "log_meal"),
    ("я выпил", "log_meal"),
    ("выпил", "log_meal"),
    ("завтрак", "log_meal"),
    ("обед", "log_meal"),
    ("ужин", "log_meal"),
    ("перекус", "log_meal"),
    ("взвес", "log_weight"),
    ("вес ", "log_weight"),
]

def _rule_intent(text: str) -> str | None:
    t = (text or "").lower()
    for needle, tool in INTENT_RULES:
        if needle in t:
            return tool
    return None


def llm_route(user_text: str, user_id: int) -> str:
    """
    Главная функция маршрутизации с использованием LangChain Agent.
    Сохраняет совместимость с текущей логикой.
    """
    t = (user_text or "").lower().strip()

    # ——— Подтверждение/отмена (высший приоритет) ———
    if t in {"да", "ок", "окей", "согласен", "подтверждаю"}:
        result = confirm_pending_action(user_id)
        memory = get_or_create_memory(user_id)
        memory.save_context({"input": user_text}, {"output": result})
        return result
        
    if t in {"нет", "не", "отмена", "отменить"}:
        result = cancel_pending_action(user_id)
        memory = get_or_create_memory(user_id)
        memory.save_context({"input": user_text}, {"output": result})
        return result

    # ——— Быстрая цель (второй приоритет) ———
    # Проверяем "цель X" или "похудеть на X кг"
    if ("цель" in t and re.search(r"(\d+(?:[.,]\d+)?)", t)) or \
       ("похуд" in t and "кг" in t and re.search(r"(\d+(?:[.,]\d+)?)", t)):
        result = propose_weight_loss_plan(user_id, user_text)
        memory = get_or_create_memory(user_id)
        memory.save_context({"input": user_text}, {"output": result})
        return result

    # ——— Жёсткие правила (третий приоритет) ———
    forced = _rule_intent(user_text)
    if forced:
        if forced == "workout":
            result = generate_workout(user_id, user_text)
        elif forced == "progress":
            result = analyze_progress(user_id)
        elif forced == "get_remaining_calories":
            result = get_remaining_calories(user_id)
        elif forced == "show_weight":
            result = show_current_weight(user_id)
        elif forced == "show_goal":
            result = show_current_goal(user_id)
        elif forced == "log_weight":
            m = re.search(r"(\d+(?:[.,]\d+)?)", user_text or "")
            if m:
                result = log_weight_entry(user_id, float(m.group(1).replace(",", ".")))
            else:
                result = "Не смог распознать вес. Пример: «взвесился 85.4»"
        elif forced == "log_meal":
            result = log_meal(user_id, user_text)
        else:
            result = small_talk(user_id, user_text)
        
        memory = get_or_create_memory(user_id)
        memory.save_context({"input": user_text}, {"output": result})
        return result

    # ——— LangChain Agent (последний приоритет) ———
    try:
        print(f"[AGENT] Calling LangChain agent for user {user_id}: {user_text}")
        
        agent_executor = create_fitness_agent(user_id)
        memory = get_or_create_memory(user_id)
        
        # Получаем историю из memory
        history = memory.load_memory_variables({})
        
        response = agent_executor.invoke({
            "input": user_text,
        })
        
        result = response.get("output", "")
        
        # Сохраняем в память
        memory.save_context({"input": user_text}, {"output": result})
        
        print(f"[AGENT] Response: {result}")
        return result
        
    except Exception as e:
        print(f"[AGENT ERROR] {e}")
        # Fallback на старую логику
        result = small_talk(user_id, user_text)
        memory = get_or_create_memory(user_id)
        memory.save_context({"input": user_text}, {"output": result})
        return result