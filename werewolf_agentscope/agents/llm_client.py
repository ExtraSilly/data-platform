"""
LLMClient – wrapper gọi Claude API để sinh ngôn ngữ tự nhiên cho agents.

Thiết kế:
  - Hỗ trợ Claude (anthropic library), model claude-haiku-4-5-20251001
  - Lazy init: chỉ khởi tạo client khi lần đầu gọi generate()
  - Fallback hoàn toàn im lặng: trả None nếu không có API key hoặc lỗi
  - Caller (BaseAgent.speak) tự dùng rule-based discuss() khi nhận None

Cách cấu hình:
  Tạo file .env (hoặc set environment variable):
      ANTHROPIC_API_KEY=sk-ant-...

Cách dùng:
  from agents.llm_client import generate
  text = generate(system_prompt, user_message)   # None nếu không có key
"""

import os

_client = None          # singleton, khởi tạo lần đầu
_available: bool | None = None  # cache trạng thái availability


def _init() -> bool:
    """Khởi tạo Anthropic client. Trả True nếu thành công."""
    global _client, _available
    if _available is not None:
        return _available

    # Thử load .env nếu có python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        _available = False
        return False

    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        _available = True
        print("[LLMClient] Claude API ready (claude-haiku-4-5-20251001)")
    except ImportError:
        print("[LLMClient] Thư viện 'anthropic' chưa cài. Chạy: pip install anthropic")
        _available = False
    except Exception as e:
        print(f"[LLMClient] Lỗi khởi tạo API: {e}")
        _available = False

    return _available


def is_available() -> bool:
    """Kiểm tra LLM có sẵn sàng không."""
    return _init()


def generate(system_prompt: str, user_message: str, max_tokens: int = 100) -> str | None:
    """
    Gọi Claude API để sinh text.

    Args:
        system_prompt: Hướng dẫn vai trò và nhiệm vụ cho agent
        user_message:  Context game hiện tại (round, alive, memory, belief)
        max_tokens:    Giới hạn độ dài output (mặc định 100 ≈ 1-2 câu)

    Returns:
        Chuỗi text ngôn ngữ tự nhiên, hoặc None nếu không available / lỗi
    """
    if not _init():
        return None

    try:
        message = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = message.content[0].text.strip()
        # Loại bỏ trích dẫn dư thừa nếu model trả về trong quotes
        text = text.strip('"').strip("'")
        return text if text else None
    except Exception as e:
        # Im lặng, để caller fallback về rule-based
        return None
