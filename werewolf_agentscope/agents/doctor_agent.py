"""
DoctorAgent – vai Bác Sĩ.

Chiến lược (Decision Policy):
  - Đêm: bảo vệ người CÓ KHẢ NĂNG bị giết cao nhất
      → người bị nhắc tên nhiều (hay dẫn dắt, dễ bị nhắm)
      → KHÔNG bảo vệ cùng 1 người 2 đêm liên tiếp (luật game)
      → bảo vệ bản thân nếu cảm thấy bị nghi ngờ
  - Ngày: quan sát, không lộ vai trò
  - Bỏ phiếu: loại người nghi ngờ nhất theo belief

📌 last_saved đảm bảo không lặp lại → thể hiện memory ảnh hưởng quyết định.
"""

import random
from .base_agent import BaseAgent


class DoctorAgent(BaseAgent):

    def __init__(self, name: str):
        super().__init__(name, role="doctor")
        # Memory đặc biệt: ai vừa được cứu đêm trước
        self.last_saved: str | None = None

    # ── DECIDE (override abstract) ────────────────────────────────────
    def decide(self, game_state) -> dict:
        """
        Quyết định hành động theo pha:
          Phase "night" → chọn người để bảo vệ
          Phase "vote"  → chọn người để bỏ phiếu
          Phase "day"   → trả về câu phát biểu
        """
        if game_state.phase == "night":
            return self._decide_save(game_state)
        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            return {"action": "vote", "target": self.vote(candidates)}
        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    # ── NIGHT: chọn người bảo vệ ─────────────────────────────────────
    def _decide_save(self, game_state) -> dict:
        """
        Học từ lịch sử: ai thường bị nhắm → bảo vệ họ.

        Ưu tiên theo thứ tự:
          1. Loại người vừa được cứu đêm trước (luật: không cứu liên tiếp)
          2. "Threat score" dựa trên lịch sử bị nhắm:
               threat = lần bị nhắm đêm qua × 2.0  (học từ pattern)
                      + influence (số lần bị nhắc ngày) × 0.7
                      + (1 - belief) × 0.3 (ưu tiên dân thường tin tưởng)
          3. Self-preservation nếu bị đổ nghi ngờ nhiều
          4. Fallback: random
        """
        alive = game_state.alive

        # Loại người vừa được cứu đêm trước
        candidates = [p for p in alive if p != self.last_saved]
        if not candidates:
            candidates = list(alive)   # fallback nếu chỉ còn 1 người

        # Kiểm tra self-preservation: đếm số lần tên ta bị đổ nghi
        accusations_on_me = sum(
            1 for e in self.memory
            if self.name in e.get("event", "") or self.name in e.get("msg", "")
        )
        if accusations_on_me >= 2 and self.name in candidates:
            target = self.name
        else:
            # Tính threat score cho từng ứng viên
            scores = {}
            for p in candidates:
                # Pattern học: ai bị kill đêm qua (nhưng được cứu) → ưu tiên cao
                was_targeted = sum(
                    1 for e in self.memory
                    if "bi giet" in e.get("event", "")
                    and p in e.get("event", "")
                )
                # Influence: số lần tên p bị nhắc trong thảo luận ngày
                influence = sum(
                    1 for e in self.memory
                    if e.get("source") not in ("self", "oracle", "system")
                    and (p in e.get("event", "") or p in e.get("msg", ""))
                )
                # Người ít bị nghi (belief thấp) → dân thường → cần bảo vệ
                trust = 1.0 - self.belief.get(p, 0.5)
                scores[p] = was_targeted * 2.0 + influence * 0.7 + trust * 0.3

            # Chọn người có threat score cao nhất
            max_score = max(scores.values())
            top = [p for p, s in scores.items() if s == max_score]
            # Tie-break: random để không bị đoán
            target = random.choice(top) if len(top) > 1 else top[0]

            # Nếu tất cả điểm = 0 (chưa có memory) → random
            if max_score == 0.0:
                target = random.choice(candidates)

        self.last_saved = target
        self.remember(
            game_state.round,
            f"Ta bao ve {target} dem nay (last_saved cap nhat).",
            source="self",
        )
        return {"action": "save", "target": target}

    # ── DAY: quan sát, không lộ vai ───────────────────────────────────
    def discuss(self, game_state) -> str:
        """Nhận xét dựa trên quan sát, không bao giờ tự khai là Bác Sĩ."""
        suspects = [p for p in game_state.alive if p != self.name]
        if not suspects:
            return f"{self.name}: Moi nguoi hay can than."

        # Nhận xét người hay im lặng (influence thấp trong memory)
        influence = {
            p: sum(
                1 for e in self.memory
                if p in e.get("event", "") or p in e.get("msg", "")
            )
            for p in suspects
        }
        quietest = min(suspects, key=lambda p: influence[p])
        most_vocal = max(suspects, key=lambda p: influence[p])

        # Bình luận dựa trên quan sát thực tế từ memory
        if influence[quietest] == 0:
            return (
                f"{self.name}: Toi thay {quietest} qua im lang, "
                f"dieu do kha bat thuong."
            )
        return (
            f"{self.name}: {most_vocal} noi nhieu nhung "
            f"hay kiem tra lai dong co cua ho."
        )

    # ── VOTE ─────────────────────────────────────────────────────────
    def vote(self, candidates: list[str]) -> str:
        return self.most_suspected(candidates)

    # ── Wrapper tương thích GameMaster ───────────────────────────────
    def night_action(self, game_state) -> dict:
        return self._decide_save(game_state)
