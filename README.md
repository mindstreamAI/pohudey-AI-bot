# 🏋️ Fitness Coach AI Bot - LangChain Version

## 📋 Описание проекта

Telegram-бот для фитнеса, построенный на базе LangChain. Помогает пользователям отслеживать питание, вес и создавать персонализированные планы похудения с использованием AI.

## 🏗️ Архитектура LangChain

### 1. **LangChain Agent (ReAct)** 
**Файл:** `router.py`

Центральный компонент системы, использующий `create_react_agent` и `AgentExecutor`. Агент анализирует запросы пользователя, принимает решения о выборе инструментов и может комбинировать несколько действий для выполнения сложных задач.
```python
agent = create_react_agent(llm, wrapped_tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=wrapped_tools,
    verbose=True,
    max_iterations=5
)
```

### 2. **LangChain Tools**
**Файл:** `tools.py`

8 инструментов с декоратором `@tool`:
- `log_meal_tool` - логирование питания
- `get_remaining_calories_tool` - остаток калорий
- `log_weight_tool` - сохранение веса
- `create_plan_tool` - создание плана
- `generate_workout_tool` - генерация тренировки
- `show_progress_tool` - показать прогресс
- `show_weight_tool` - текущий вес
- `show_goal_tool` - текущая цель

Каждый tool имеет docstring с описанием, который агент использует для выбора правильного инструмента.
```python
@tool
def log_meal_tool(user_id: int, description: str) -> str:
    """
    Логирует приём пищи пользователя. Автоматически оценивает калории через AI.
    
    Args:
        user_id: ID пользователя в Telegram
        description: Описание еды (например: "2 яйца", "борщ 300 мл")
    
    Returns:
        Сообщение с подтверждением и статистикой калорий за день
    """
    return log_meal(user_id, description)
```

### 3. **Conversational Memory**
**Файл:** `router.py`

`ConversationBufferMemory` хранит историю диалога для каждого пользователя отдельно, позволяя боту вести связный разговор и понимать контекст предыдущих сообщений.
```python
user_memories: Dict[int, ConversationBufferMemory] = {}

def get_or_create_memory(user_id: int) -> ConversationBufferMemory:
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[user_id]
```

### 4. **ChatOpenAI LLM**
**Файл:** `config.py`

LLM модель из `langchain-openai`, которая используется агентом для reasoning и генерации ответов.
```python
def get_llm():
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=OPENAI_MODEL,
        temperature=OPENAI_TEMPERATURE,
    )
```

## 📁 Структура проекта
```
├── config.py           # Конфигурация и LangChain LLM
├── router.py           # LangChain Agent + Memory
├── tools.py            # LangChain Tools (@tool декораторы)
├── agent.py            # Вспомогательные функции для LLM
├── database.py         # Работа с SQLite БД
├── telegram_bot.py     # Telegram Bot интеграция
├── main.py             # Точка входа
├── utils.py            # Утилиты
├── parse.py            # Парсинг (fallback)
└── requirements.txt    # Зависимости
```

## 🚀 Установка и запуск

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```

Установятся:
- `langchain` - основной фреймворк
- `langchain-openai` - интеграция с OpenAI
- `langgraph` - для агентов
- `aiogram` - Telegram бот
- `python-dotenv` - переменные окружения
- `openai` - OpenAI API

### 2. Настройте .env файл

Создайте файл `.env` в корне проекта:
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# LangSmith (опционально, для трейсинга)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_langsmith_key_here
```

### 3. Запустите бота
```bash
python main.py
```

Должно появиться:
```
==================================================
🏋️ Fitness Coach AI Bot
==================================================
✓ Инициализирую БД...
✓ Запускаю Telegram бота...
🤖 Bot polling...
```

## 💬 Примеры использования

### Создание профиля
```
Пользователь: Юрий, 38, 88, 175
Бот: ✅ Профиль сохранён: Юрий, 38 лет, 88.0 кг, 175 см
```

### Создание плана похудения
```
Пользователь: похудеть на 10 кг за 12 недель
Бот: 🎯 Цель: 78.0 кг (текущий 88.0 кг)
     🍽️ Калораж: ~1766 ккал/день (TDEE ~2683 ккал)
     🥗 Макросы: белки 156 г, углеводы 161 г, жиры 55 г
     ⏰ Срок: ~12 нед.
     
     Подходит? Напиши: «да» — применить, «нет» — отмена

Пользователь: да
Бот: ✅ План применён!
```

### Логирование питания с памятью контекста# 🏋️ Fitness Coach AI Bot - LangChain Version

## 📋 Описание проекта

Telegram-бот для фитнеса, построенный на базе LangChain. Помогает пользователям отслеживать питание, вес и создавать персонализированные планы похудения с использованием AI.

## 🏗️ Архитектура LangChain

### 1. **LangChain Agent (ReAct)** 
**Файл:** `router.py`

Центральный компонент системы, использующий `create_react_agent` и `AgentExecutor`. Агент анализирует запросы пользователя, принимает решения о выборе инструментов и может комбинировать несколько действий для выполнения сложных задач.
```python
agent = create_react_agent(llm, wrapped_tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=wrapped_tools,
    verbose=True,
    max_iterations=5
)
```

### 2. **LangChain Tools**
**Файл:** `tools.py`

8 инструментов с декоратором `@tool`:
- `log_meal_tool` - логирование питания
- `get_remaining_calories_tool` - остаток калорий
- `log_weight_tool` - сохранение веса
- `create_plan_tool` - создание плана
- `generate_workout_tool` - генерация тренировки
- `show_progress_tool` - показать прогресс
- `show_weight_tool` - текущий вес
- `show_goal_tool` - текущая цель

Каждый tool имеет docstring с описанием, который агент использует для выбора правильного инструмента.
```python
@tool
def log_meal_tool(user_id: int, description: str) -> str:
    """
    Логирует приём пищи пользователя. Автоматически оценивает калории через AI.
    
    Args:
        user_id: ID пользователя в Telegram
        description: Описание еды (например: "2 яйца", "борщ 300 мл")
    
    Returns:
        Сообщение с подтверждением и статистикой калорий за день
    """
    return log_meal(user_id, description)
```

### 3. **Conversational Memory**
**Файл:** `router.py`

`ConversationBufferMemory` хранит историю диалога для каждого пользователя отдельно, позволяя боту вести связный разговор и понимать контекст предыдущих сообщений.
```python
user_memories: Dict[int, ConversationBufferMemory] = {}

def get_or_create_memory(user_id: int) -> ConversationBufferMemory:
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return user_memories[user_id]
```

### 4. **ChatOpenAI LLM**
**Файл:** `config.py`

LLM модель из `langchain-openai`, которая используется агентом для reasoning и генерации ответов.
```python
def get_llm():
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=OPENAI_MODEL,
        temperature=OPENAI_TEMPERATURE,
    )
```

## 📁 Структура проекта
```
├── config.py           # Конфигурация и LangChain LLM
├── router.py           # LangChain Agent + Memory
├── tools.py            # LangChain Tools (@tool декораторы)
├── agent.py            # Вспомогательные функции для LLM
├── database.py         # Работа с SQLite БД
├── telegram_bot.py     # Telegram Bot интеграция
├── main.py             # Точка входа
├── utils.py            # Утилиты
├── parse.py            # Парсинг (fallback)
└── requirements.txt    # Зависимости
```

## 🚀 Установка и запуск

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```

Установятся:
- `langchain` - основной фреймворк
- `langchain-openai` - интеграция с OpenAI
- `langgraph` - для агентов
- `aiogram` - Telegram бот
- `python-dotenv` - переменные окружения
- `openai` - OpenAI API

### 2. Настройте .env файл

Создайте файл `.env` в корне проекта:
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# LangSmith (опционально, для трейсинга)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_langsmith_key_here
```

### 3. Запустите бота
```bash
python main.py
```

Должно появиться:
```
==================================================
🏋️ Fitness Coach AI Bot
==================================================
✓ Инициализирую БД...
✓ Запускаю Telegram бота...
🤖 Bot polling...
```

## 💬 Примеры использования

### Создание профиля
```
Пользователь: Юрий, 38, 88, 175
Бот: ✅ Профиль сохранён: Юрий, 38 лет, 88.0 кг, 175 см
```

### Создание плана похудения
```
Пользователь: похудеть на 10 кг за 12 недель
Бот: 🎯 Цель: 78.0 кг (текущий 88.0 кг)
     🍽️ Калораж: ~1766 ккал/день (TDEE ~2683 ккал)
     🥗 Макросы: белки 156 г, углеводы 161 г, жиры 55 г
     ⏰ Срок: ~12 нед.
     
     Подходит? Напиши: «да» — применить, «нет» — отмена

Пользователь: да
Бот: ✅ План применён!
```

### Логирование питания с памятью контекста
