import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv
from models import MixBotMessage
from prompts import CHAT_SYSTEM_PROMPT, JSON_SYSTEM_PROMPT

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment")

genai.configure(api_key=API_KEY or "not_set")

# Gemini model
MODEL = "gemini-2.0-flash"


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
        return {
            "name": "Oops, formatting error",
            "ingredients": ["1 error log"],
            "measurements": ["1 oz"],
            "instructions": ["Please try again."],
            "glassware": "Glass",
            "garnish": "None",
            "difficulty": "Easy",
            "flavor_profile": "",
            "fun_fact": ""
        }


def _generate_json(prompt: str, temperature: float = 0.2):
    try:
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=JSON_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(temperature=temperature)
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini JSON API Error: {e}")
        return "{}"


def _generate_chat(messages_list: list, temperature: float = 0.7):
    """
    messages_list is in OpenAI format: [{"role": "system"|"user"|"assistant", "content": "..."}]
    We convert to Gemini format for multi-turn chat.
    """
    try:
        # Extract system instruction (first message if role == "system")
        system_instruction = None
        history = []
        user_message = None

        for msg in messages_list:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                user_message = msg["content"]
                # All prior user messages go to history
                if len(messages_list) > messages_list.index(msg) + 1:
                    history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"]]})

        # The last user message is the one we send now
        # Rebuild: history = all except last user message
        gemini_history = []
        all_turns = [m for m in messages_list if m["role"] != "system"]
        for i, msg in enumerate(all_turns[:-1]):  # all but last
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        last_msg = all_turns[-1]["content"] if all_turns else ""

        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=system_instruction or CHAT_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(temperature=temperature)
        )
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(last_msg)
        return response.text
    except Exception as e:
        print(f"Gemini Chat API Error: {e}")
        raise e


def suggest_cocktails(ingredients, mood, style, sweetness, lightness, fruitiness):
    prompt = (
        f"I have these ingredients: {', '.join(ingredients)}. "
        f"I'm in a {mood} mood and prefer a {style} style. "
        f"I like sweetness at {sweetness}%, lightness at {lightness}%, and fruitiness at {fruitiness}%. "
        f"Create a cocktail recipe for me. Ensure you reply with ONLY a single JSON object matching the RecipeResponse format."
    )
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
            if "429" in error_msg or "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
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
