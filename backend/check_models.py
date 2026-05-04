import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("No API Key found! Make sure GEMINI_API_KEY is in your .env file.")
else:
    print(f"Key loaded: {API_KEY[:5]}...{API_KEY[-4:]}")
    genai.configure(api_key=API_KEY)

    try:
        print("\nFetching available models for your specific API key...")
        models = list(genai.list_models())
        supported = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        if supported:
            print("SUCCESS! Your key supports the following models:")
            for m in supported:
                print(f" - {m}")
        else:
            print("Your key is valid, but it doesn't have access to any generateContent models! (Are you using an old or restricted key?)")
    except Exception as e:
        print("\nERROR FETCHING MODELS:")
        print(e)
