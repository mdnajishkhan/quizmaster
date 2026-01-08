import google.generativeai as genai
import os

# Use the API key directly for the test
api_key = 'AIzaSyAZiCoN3SVYVpdJacJNHFdF9VJwomE1JnM'
genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
