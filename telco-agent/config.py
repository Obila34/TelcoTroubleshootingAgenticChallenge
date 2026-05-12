import os
from pathlib import Path

from dotenv import load_dotenv

# Always load telco-agent/.env (not only when cwd is telco-agent).
load_dotenv(Path(__file__).resolve().parent / ".env")

# --- Competition Agent CLI API (Track B README) ---
# Single endpoint; JSON body: device_name, command, question_number (all strings).
# China ELB vs overseas HK ECS — pick one or set AGENT_EXECUTE_URL explicitly.
URL_AGENT_EXECUTE_CHINA = "https://120.46.145.77/ip/api/agent/execute"
URL_AGENT_EXECUTE_OVERSEAS = "https://124.71.227.61/ip/api/agent/execute"

AGENT_REGION = os.getenv("AGENT_REGION", "overseas").strip().lower()
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

AGENT_EXECUTE_URL = os.getenv(
    "AGENT_EXECUTE_URL",
    URL_AGENT_EXECUTE_CHINA if AGENT_REGION == "china" else URL_AGENT_EXECUTE_OVERSEAS,
)

# README uses verify=False for self-signed public IPs; set VERIFY_SSL=true to enforce TLS verify.
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").strip().lower() in ("1", "true", "yes")

# Legacy local stub only (optional); real Track B flow uses AGENT_EXECUTE_URL above.
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

# --- LLM (OpenAI-compatible: Together, DashScope compatible-mode, local vLLM, etc.) ---
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.together.xyz/v1").strip()
LLM_API_KEY = (
    os.getenv("LLM_API_KEY", "").strip()
    or os.getenv("DASHSCOPE_API_KEY", "").strip()
    or os.getenv("GEMINI_API_KEY", "").strip()
    or os.getenv("GOOGLE_API_KEY", "").strip()
    or os.getenv("TOGETHER_API_KEY", "").strip()
)
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct-Turbo").strip()

_hf_router = "router.huggingface.co" in LLM_BASE_URL
if _hf_router and not LLM_API_KEY:
    raise RuntimeError(
        "LLM_API_KEY is empty but LLM_BASE_URL points at Hugging Face. "
        "Set LLM_API_KEY to your HF token (Settings → Access Tokens) in telco-agent/.env."
    )
if _hf_router and not LLM_MODEL:
    raise RuntimeError(
        "LLM_MODEL is empty. Set it to the exact model id from the Hugging Face model page "
        "(e.g. open the model → copy id for Inference)."
    )

_gemini = "generativelanguage.googleapis.com" in LLM_BASE_URL
if _gemini and not LLM_API_KEY:
    raise RuntimeError(
        "Using Gemini OpenAI-compatible endpoint but no API key. "
        "Set GEMINI_API_KEY or GOOGLE_API_KEY (from https://aistudio.google.com/apikey ) in telco-agent/.env."
    )

_dashscope = "dashscope" in LLM_BASE_URL.lower()
if _dashscope and not LLM_API_KEY:
    raise RuntimeError(
        "DashScope base URL set but no API key. Set DASHSCOPE_API_KEY (from Alibaba Model Studio) in telco-agent/.env."
    )
if _dashscope and not LLM_MODEL:
    raise RuntimeError(
        "LLM_MODEL is empty. Set it to the exact DashScope model code from Model Studio "
        "(e.g. qwen3.5-35b-a3b — copy what the console shows for Qwen3.5-35B-A3B)."
    )

# Model-side tool turns per question (README allows up to 500 API calls per scenario per token).
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))
ANSWER_TIMEOUT = 240
