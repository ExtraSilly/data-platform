"""
SeerAgent – vai Tiên Tri.

Chiến lược (Decision Policy):
  - Đêm: kiểm tra 1 người chưa được kiểm tra, ưu tiên người nghi ngờ nhất
  - Kết quả lưu vào memory riêng tư (KHÔNG chia sẻ ngay)
  - Belief tăng lên 1.0 nếu là sói, giảm về 0.0 nếu là dân
  - Ngày: tiết lộ gợi ý thận trọng (không khai toàn bộ để tránh bị giết)
  - Bỏ phiếu: ưu tiên người đã xác nhận là Ma Sói

📌 Thông tin riêng tư: self.checked không ai ngoài Seer đọc được.
"""

import random
from .base_agent import BaseAgent


class SeerAgent(BaseAgent):

    def __init__(self, name: str):
        super().__init__(name, role="seer")
        # Memory mở rộng: kết quả kiểm tra riêng tư
        # {tên: "werewolf" | "villager"}  – chỉ Seer biết
        self.checked: dict[str, str] = {}

    # ── DECIDE (override abstract) ────────────────────────────────────
    def decide(self, game_state) -> dict:
        """
        Quyết định hành động theo pha:
          Phase "night" → chọn người để kiểm tra
          Phase "vote"  → chọn người để bỏ phiếu
          Phase "day"   → trả về câu phát biểu
        """
        if game_state.phase == "night":
            return self._decide_check(game_state)
        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            return {"action": "vote", "target": self.vote(candidates)}
        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    # ── NIGHT: chọn 1 người để kiểm tra ─────────────────────────────
    def _decide_check(self, game_state) -> dict:
        """
        Ưu tiên:
          1. Người nghi ngờ nhất (belief cao) chưa được kiểm tra
          2. Nếu tất cả đã check → random trong danh sách chưa check
          3. Fallback: không hành động
        """
        unchecked = [
            p for p in game_state.alive
            if p != self.name and p not in self.checked
        ]
        if not unchecked:
            # Tất cả đã check – chọn lại random (hiếm gặp)
            unchecked = [p for p in game_state.alive if p != self.name]

        if not unchecked:
            return {"action": "check", "target": None}

        # Chọn người nghi ngờ nhất trong số chưa check
        # Nếu belief đều bằng nhau → random (tránh bias)
        beliefs = {p: self.belief.get(p, 0.5) for p in unchecked}
        max_val = max(beliefs.values())
        top_suspects = [p for p, v in beliefs.items() if v == max_val]
        target = random.choice(top_suspects)   # random khi tie

        self.remember(
            game_state.round,
            f"Ta kiem tra {target} dem nay.",
            source="self",
        )
        return {"action": "check", "target": target}

    # ── Nhận kết quả từ GameMaster (thông tin riêng tư) ──────────────
    def receive_check_result(self, target: str, result: str, round_num: int) -> None:
        """
        GameMaster gọi method này sau khi Seer chọn mục tiêu.
        Thông tin được lưu vào self.checked – KHÔNG ai ngoài Seer biết.

        result: "werewolf" | "villager"
        """
        self.checked[target] = result

        # Ghi vào memory riêng tư với source="oracle" (thông tin đặc quyền)
        self.remember(
            round_num,
            f"[BI MAT] {target} la: {result.upper()}.",
            source="oracle",
        )

        # Cập nhật belief ngay lập tức
        if result == "werewolf":
            self.belief[target] = 1.0    # chắc chắn là Ma Sói
        else:
            self.belief[target] = 0.0    # tin tưởng hoàn toàn

        print(
            f"  [Tien Tri - chi minh biet] "
            f"{target} -> {result.upper()}"
        )

    # ── LLM: system prompt theo vai Tiên Tri ─────────────────────────
    def _system_prompt(self, game_state) -> str:
        alive = game_state.alive
        alive_wolves    = [p for p, r in self.checked.items() if r == "werewolf" and p in alive]
        alive_villagers = [p for p, r in self.checked.items() if r == "villager" and p in alive]

        known_danger = len(alive_wolves) / max(len(alive), 1)
        critical = len(alive) <= 4 or known_danger >= 0.3

        wolf_info = f"đã xác nhận là Ma Sói: {', '.join(alive_wolves)}" if alive_wolves else "chưa tìm ra Ma Sói"
        safe_info = f"Đã xác nhận vô tội: {', '.join(alive_villagers)}. " if alive_villagers else ""

        if critical and alive_wolves:
            task = (
                f"Tình huống NGUY CẤP! Hãy tiết lộ thẳng rằng bạn là Tiên Tri "
                f"và {alive_wolves[0]} chắc chắn là Ma Sói. Kêu gọi mọi người bỏ phiếu loại ngay."
            )
        elif alive_wolves:
            task = (
                f"Hãy gợi ý kín đáo mọi người để ý đến {alive_wolves[0]} "
                f"mà không tiết lộ bạn là Tiên Tri (tránh bị Ma Sói nhắm)."
            )
        else:
            suspects = [p for p in alive if p != self.name]
            top = self.most_suspected(suspects) if suspects else "ai đó"
            task = f"Chia sẻ quan sát tự nhiên, gợi ý {top} có vẻ đáng ngờ."

        return (
            f"Bạn tên {self.name}, đang chơi Ma Sói. Vai trò bí mật: TIÊN TRI. "
            f"Thông tin oracle (chỉ bạn biết): {wolf_info}. {safe_info}"
            f"{task} "
            f"Trả lời bằng tiếng Việt, 1-2 câu, chỉ câu phát biểu, không có gì thêm."
        )

    # ── DAY: tiết lộ thận trọng, chỉ công bố khi có bằng chứng mạnh ──
    def discuss(self, game_state) -> str:
        """
        Chiến lược tiết lộ 3 tầng:
          Tier 1 – Nguy cấp (sắp thua): khai thẳng tên Ma Sói
          Tier 2 – Có bằng chứng: gợi ý tập trung + bảo vệ dân vô tội
          Tier 3 – Chưa đủ bằng chứng: im lặng quan sát
        """
        alive = game_state.alive
        alive_wolves = [p for p, r in self.checked.items()
                        if r == "werewolf" and p in alive]
        alive_villagers = [p for p, r in self.checked.items()
                           if r == "villager" and p in alive]

        # Tính áp lực: wolves đã biết / tổng người sống
        known_danger = len(alive_wolves) / max(len(alive), 1)
        total_alive  = len(alive)
        # Nguy cấp: ít hơn 4 người hoặc đã xác nhận Ma Sói đang còn sống
        critical = total_alive <= 4 or known_danger >= 0.3

        # ── Tier 1: nguy cấp → khai thẳng, lộ bản thân ───────────────
        if alive_wolves and critical:
            target = alive_wolves[0]
            return (
                f"{self.name}: Toi la Tien Tri. "
                f"Toi xac nhan {target} chinh xac la Ma Soi! "
                f"Hay bo phieu loai ngay!"
            )

        # ── Tier 2: có bằng chứng, chưa nguy cấp → gợi ý kín đáo ────
        if alive_wolves:
            target = alive_wolves[0]
            return (
                f"{self.name}: Toi co thong tin dang tin cay – "
                f"moi nguoi hay chu y den {target}."
            )

        if alive_villagers:
            safe = alive_villagers[0]
            return f"{self.name}: Toi dam bao {safe} hoan toan vo toi."

        # ── Tier 3: chưa có gì chắc chắn → giả vờ bình thường ────────
        suspects = [p for p in alive if p != self.name]
        if suspects:
            # Gợi ý nhẹ dựa trên belief (không lộ nguồn)
            top = self.most_suspected(suspects)
            return f"{self.name}: Toi dang theo doi, {top} co ve kha nghi ngo."
        return f"{self.name}: Toi dang quan sat, chua co ket luan."

    # ── VOTE: ưu tiên loại Ma Sói đã xác nhận ────────────────────────
    def vote(self, candidates: list[str]) -> str:
        # Xác nhận là sói → vote trước
        confirmed_wolves = [
            p for p in candidates
            if self.checked.get(p) == "werewolf"
        ]
        if confirmed_wolves:
            return confirmed_wolves[0]
        # Chưa xác nhận → dùng belief
        return self.most_suspected(candidates)

    # ── Wrapper cho GameMaster (tương thích) ─────────────────────────
    def night_action(self, game_state) -> dict:
        return self._decide_check(game_state)
