# app/memory_store.py

conversation_memory = {}  # {employee_id: [{"input": ..., "output": ...}, ...]}

def save_conversation(employee_id: int, user_input: str, ai_output: str):
    if employee_id not in conversation_memory:
        conversation_memory[employee_id] = []
    conversation_memory[employee_id].append({
        "input": user_input,
        "output": ai_output
    })

def get_conversation_history(employee_id: int) -> list[dict]:
    return conversation_memory.get(employee_id, [])
