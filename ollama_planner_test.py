import requests
import time

t = time.time()

print("CALLING QWEN3:8B PLANNER...")

payload = {
    "model": "qwen3:8b",
    "messages": [
        {
            "role": "system",
            "content": "You are a semantic planner. Return JSON only."
        },
        {
            "role": "user",
            "content": 'Plan a read-only database search for: Show me all critical alerts. Return exactly {"reasoning":"brief","calls":[{"tool":"search_alerts","arguments":{"severity":"critical"}}]}'
        }
    ],
    "stream": False,
    "think": False,
    "options": {
        "temperature": 0.0,
        "num_predict": 120
    }
}

r = requests.post(
    "http://localhost:11434/api/chat",
    json=payload,
    timeout=180
)

print("TIME:", round(time.time() - t, 2), "sec")
print("STATUS:", r.status_code)
print("RESPONSE:")
print(r.json().get("message", {}).get("content", ""))
