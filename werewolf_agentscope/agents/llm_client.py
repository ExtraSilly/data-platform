"""
LLMClient – wrapper đa nhà cung cấp LLM cho agents.

Hỗ trợ 3 provider, chọn qua biến môi trường LLM_PROVIDER:
  - "gemini"    : Google Gemini Flash (miễn phí 1500 req/ngày) ← MẶC ĐỊNH
  - "ollama"    : Chạy local hoàn toàn miễn phí (cần cài Ollama)
  - "claude"    : Anthropic Claude Haiku (trả phí)

Cách cấu hình (.env):
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=AIza...          # lấy miễn phí tại aistudio.google.com

  LLM_PROVIDER=ollama
  OLLAMA_MODEL=qwen2.5:3b         # hoặc llama3.2, gemma3, v.v.
  OLLAMA_URL=http://localhost:11434  # mặc định

  LLM_PROVIDER=claude
  ANTHROPIC_API_KEY=sk-ant-...

Nếu không cấu hình gì → fallback về rule-based discuss() tự động.
"""

import os

_provider: str | None = None   # "gemini" | "ollama" | "claude" | None
_client = None                  # client object (Gemini / Anthropic)
_initialized = False


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _init() -> bool:
    """Khởi tạo provider một lần duy nhất. Trả True nếu thành công."""
    global _provider, _client, _initialized
    if _initialized:
        return _provider is not None
    _initialized = True
    _load_env()

    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()

    # ── Gemini ──────────────────────────────────────────────────────────
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            print("[LLMClient] GEMINI_API_KEY chưa đặt. Fallback rule-based.")
            return False
        try:
            from google import genai
            _client = genai.Client(api_key=key)
            _provider = "gemini"
            print("[LLMClient] Gemini 2.5 Flash Lite ready (miễn phí)")
            return True
        except ImportError:
            print("[LLMClient] Chưa cài google-genai. Chạy: pip install google-genai")
        except Exception as e:
            print(f"[LLMClient] Gemini lỗi: {e}")
        return False

    # ── Ollama (local) ───────────────────────────────────────────────────
    if provider == "ollama":
        _provider = "ollama"
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        url   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        # Kiểm tra Ollama đang chạy không
        try:
            import requests
            requests.get(f"{url}/api/tags", timeout=3)
            print(f"[LLMClient] Ollama ready – model: {model}")
            return True
        except Exception:
            print(f"[LLMClient] Ollama chưa chạy tại {url}. Fallback rule-based.")
            _provider = None
            return False

    # ── Claude ──────────────────────────────────────────────────────────
    if provider == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            print("[LLMClient] ANTHROPIC_API_KEY chưa đặt. Fallback rule-based.")
            return False
        try:
            import anthropic
            _client = anthropic.Anthropic(api_key=key)
            _provider = "claude"
            print("[LLMClient] Claude Haiku ready")
            return True
        except ImportError:
            print("[LLMClient] Chưa cài anthropic. Chạy: pip install anthropic")
        except Exception as e:
            print(f"[LLMClient] Claude lỗi: {e}")
        return False

    # ── Không cấu hình ──────────────────────────────────────────────────
    return False


def is_available() -> bool:
    return _init()


def generate(system_prompt: str, user_message: str, max_tokens: int = 100) -> str | None:
    """
    Sinh text từ provider đã cấu hình.
    Trả None nếu không available hoặc gặp lỗi → caller fallback rule-based.
    """
    if not _init():
        return None

    prompt_full = f"{system_prompt}\n\n{user_message}"

    try:
        # ── Gemini ──────────────────────────────────────────────────────
        if _provider == "gemini":
            from google.genai import types
            resp = _client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt_full,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.8,
                ),
            )
            text = resp.text.strip().strip('"').strip("'")
            return text or None

        # ── Ollama ──────────────────────────────────────────────────────
        if _provider == "ollama":
            import requests, json
            model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
            url   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
            resp = requests.post(
                f"{url}/api/generate",
                json={"model": model, "prompt": prompt_full, "stream": False,
                      "options": {"num_predict": max_tokens, "temperature": 0.8}},
                timeout=30,
            )
            text = resp.json().get("response", "").strip().strip('"').strip("'")
            return text or None

        # ── Claude ──────────────────────────────────────────────────────
        if _provider == "claude":
            msg = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            text = msg.content[0].text.strip().strip('"').strip("'")
            return text or None

    except Exception:
        pass

    return None
