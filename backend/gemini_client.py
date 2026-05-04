import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from models import MixBotMessage
from prompts import CHAT_SYSTEM_PROMPT, JSON_SYSTEM_PROMPT

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    print("WARNING: OPENROUTER_API_KEY not found in .env")

# Initialize OpenRouter client
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=API_KEY or "not_set",
)

# OpenRouter model selection
# We're keeping Gemini 2.0 Flash since it works great, but routing it through OpenRouter
MODEL = 'google/gemini-2.0-flash-001'

def parse_json_response(text: str):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception as e:
        print("JSON Parse Error: ", e)
        return {"name": "Oops, formatting error", "ingredients": ["1 error log"], "measurements": ["1 oz"], "instructions": ["Please click 'Mix Me a Drink!' again."], "glassware": "Glass", "garnish": "None", "difficulty": "Easy", "flavor_profile": "", "fun_fact": ""}

def _generate_json(prompt: str, temperature: float = 0.2):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": JSON_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {e}")
        return "{}"

def _generate_chat(messages_list: list, temperature: float = 0.7):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages_list,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {e}")
        raise e

def suggest_cocktails(ingredients, mood, style, sweetness, lightness, fruitiness):
    prompt = f"I have these ingredients: {', '.join(ingredients)}. I'm in a {mood} mood and prefer a {style} style. I like sweetness at {sweetness}%, lightness at {lightness}%, and fruitiness at {fruitiness}%. Create a cocktail recipe for me. Ensure you reply with ONLY a single JSON object matching the RecipeResponse format."
    response_text = _generate_json(prompt, 0.2)
    return parse_json_response(response_text)

def chat_with_mixbot(history: list[MixBotMessage], new_message: str):
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for m in history:
        role = "user" if m.role == "user" else "assistant"
        messages.append({"role": role, "content": m.text})
    
    messages.append({"role": "user", "content": new_message})
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return _generate_chat(messages, 0.7)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return "MixBot is currently taking a quick break due to high demand. Please try again in a minute!"
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "MixBot encountered an error. Please try again later."

def get_random_cocktail():
    prompt = "Create a random cocktail of the day. Return ONLY a single JSON recipe object."
    response_text = _generate_json(prompt, 0.5)
    return parse_json_response(response_text)

def analyze_cocktail(name: str):
    prompt = f"Break down the cocktail: {name}. Provide its recipe as a single JSON object."
    response_text = _generate_json(prompt, 0.2)
    return parse_json_response(response_text)

def scan_ingredients(description: str):
    prompt = f"Extract a list of drink ingredients from this text: '{description}'. Return flat JSON array of strings, e.g., [\"vodka\", \"lemon\"]."
    response_text = _generate_json(prompt, 0.1)
    return parse_json_response(response_text)
    
def get_substitutions(missing: str, cocktail: str = None):
    prompt = f"I am missing {missing}" + (f" for making a {cocktail}" if cocktail else "") + ". What are some good alternatives? Speak as MixBot."
    try:
        return _generate_chat([
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ], 0.7)
    except Exception:
        return "I'm sorry, I couldn't find any substitutions right now."

def plan_party(guest_count: int, vibe: str, budget: str):
    prompt = f"Plan a party for {guest_count} guests with a {vibe} vibe on a {budget} budget. Return your response as MixBot explaining the menu, along with a structured shopping list."
    try:
        return _generate_chat([
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ], 0.8)
    except Exception:
        return "Oops, I had trouble planning the party. Please try again later."
