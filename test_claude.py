"""
Quick diagnostic: find which model name works with your API key.
Run with: python test_claude.py
"""
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODELS_TO_TRY = [
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

for model in MODELS_TO_TRY:
    try:
        r = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello"}],
        )
        print(f"  WORKS: {model}")
    except anthropic.NotFoundError:
        print(f"  NOT FOUND: {model}")
    except anthropic.BadRequestError as e:
        print(f"  BAD REQUEST: {model} -> {e}")
    except Exception as e:
        print(f"  ERROR: {model} -> {type(e).__name__}: {e}")
