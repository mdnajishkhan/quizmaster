import sys
try:
    import openai
    print(f"OpenAI found at: {openai.__file__}")
except ImportError as e:
    print(f"Error: {e}")
    print(f"Sys Path: {sys.path}")
