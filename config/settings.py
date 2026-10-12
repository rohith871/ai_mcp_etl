import os
from dotenv import load_dotenv

load_dotenv()

# Primary Provider (Groq)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Fallback Provider (NVIDIA NIM)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

# Layer 1 Speed Controls
CONCURRENT_CHECKS = 50      # Number of parallel domain checks
HTTP_TIMEOUT = 6.0          # Seconds before marking URL as unreachable

