import os
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

def test_groq():
    print("--- Testing Primary API (Groq) ---")
    if not GROQ_API_KEY:
        print("❌ Groq API Key missing in .env!\n")
        return False

    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "Respond with strictly JSON: {\"status\": \"ok\", \"provider\": \"Groq\"}"}],
            temperature=0.1,
            max_completion_tokens=256,
            stream=True
        )
        print("✅ Groq Connection Successful!")
        print("Response: ", end="")
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
        print("\n")
        return True
    except Exception as e:
        print(f"❌ Groq Connection Failed: {e}\n")
        return False

def test_nvidia_nim():
    print("--- Testing Secondary API (NVIDIA NIM) ---")
    if not NVIDIA_API_KEY:
        print("❌ NVIDIA API Key missing in .env!\n")
        return False

    try:
        client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY
        )
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": "Respond with strictly JSON: {\"status\": \"ok\", \"provider\": \"NVIDIA NIM\"}"}],
            temperature=0.1,
            max_tokens=256,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            stream=True
        )

        print("✅ NVIDIA NIM Connection Successful!")
        print("Response: ", end="")
        for chunk in completion:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
        print("\n")
        return True
    except Exception as e:
        print(f"❌ NVIDIA NIM Connection Failed: {e}\n")
        return False

if __name__ == "__main__":
    print("Starting API Key Verification...\n")
    groq_ok = test_groq()
    nvidia_ok = test_nvidia_nim()

    if groq_ok and nvidia_ok:
        print("🎉 BOTH Groq and NVIDIA NIM APIs are working perfectly!")
    else:
        print("⚠️ Check errors above.")