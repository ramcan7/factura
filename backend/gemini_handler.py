from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("models/gemini-1.5-flash")

def gemini_recall(prompt: str, temperature: float = 0.5, max_tokens: int = 60) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return "There was an error processing the request with Gemini."
