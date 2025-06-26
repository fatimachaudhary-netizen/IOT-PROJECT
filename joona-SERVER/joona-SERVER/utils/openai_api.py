from openai import OpenAI
from config import OPENROUTER_API_KEY

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def generate_chat_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. "
                        "Always keep your answers short and concise — just 1 or 2 sentences. "
                        "Avoid unnecessary details unless explicitly asked."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Joona-Backend",
            }
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenRouter error:", e)
        return "Gemini API error: " + str(e)
