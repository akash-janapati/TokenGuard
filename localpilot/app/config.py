"""Central settings. Override any of these with environment variables (or a .env file)."""
import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# Local LLM (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen2.5-coder:7b")
LOCAL_TIMEOUT_S = float(os.getenv("LOCAL_TIMEOUT_S", "120"))
LOCAL_NUM_CTX = int(os.getenv("LOCAL_NUM_CTX", "8192"))  # Ollama's default window silently truncates

# Cloud LLM: "anthropic", "openai" (any OpenAI-compatible API: OpenAI, Groq, OpenRouter...), or "mock"
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLOUD_TIMEOUT_S = float(os.getenv("CLOUD_TIMEOUT_S", "120"))
CLOUD_MAX_TOKENS = int(os.getenv("CLOUD_MAX_TOKENS", "16000"))

# Routing thresholds
LOCAL_THRESHOLD = float(os.getenv("LOCAL_THRESHOLD", "0.35"))  # score below this -> local
CLOUD_THRESHOLD = float(os.getenv("CLOUD_THRESHOLD", "0.65"))  # score above this -> cloud
MIN_LOCAL_CONFIDENCE = float(os.getenv("MIN_LOCAL_CONFIDENCE", "0.7"))  # below -> escalate

# Context budget for cloud requests
CLOUD_CONTEXT_TOKEN_BUDGET = int(os.getenv("CLOUD_CONTEXT_TOKEN_BUDGET", "3000"))
