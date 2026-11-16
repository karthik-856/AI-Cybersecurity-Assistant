import urllib.request
import urllib.error
from backend.app.assistant.llm.llm_service import zuka_llm_service

print("PROVIDER:", zuka_llm_service._selected_provider())
print("MODEL:", zuka_llm_service.openai_model)
print("KEY:", "SET" if zuka_llm_service.openai_key else "MISSING")

payload = {
    "model": zuka_llm_service.openai_model,
    "messages": [
        {"role": "user", "content": "Reply with exactly OK"}
    ],
    "max_tokens": 10,
}

request = urllib.request.Request(
    f"{zuka_llm_service.openai_base}/chat/completions",
    data=__import__("json").dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {zuka_llm_service.openai_key}",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=25) as response:
        print("STATUS:", response.status)
        print("BODY:", response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("BODY:", e.read().decode("utf-8"))
