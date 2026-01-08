import google.generativeai as genai
import os

api_key = 'AIzaSyAZiCoN3SVYVpdJacJNHFdF9VJwomE1JnM'
genai.configure(api_key=api_key)

models_to_test = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-flash-latest', 'gemini-1.5-flash-001', 'gemini-1.5-flash-002']

for model_name in models_to_test:
    print(f"Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"SUCCESS: {model_name}")
        break
    except Exception as e:
        print(f"FAILED: {model_name} - {e}")
