# agent.py
from config import openai_client, OPENAI_MODEL, OPENAI_TEMPERATURE

client = openai_client()

def call_ai(user_id: int, prompt: str, system: str = None, temperature: float | None = None) -> dict:
    """
    Универсальный вызов LLM.
    Возвращает {"response": <str>}.
    Логирует запрос/ответ.
    """
    sysmsg = system or "Отвечай кратко и по делу."
    temp = OPENAI_TEMPERATURE if temperature is None else float(temperature)

    print(f"[LLM→] uid={user_id} prompt={prompt[:400]}")
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=temp,
        messages=[
            {"role": "system", "content": sysmsg},
            {"role": "user", "content": prompt},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    print(f"[LLM←] {text[:400]}")
    return {"response": text}
