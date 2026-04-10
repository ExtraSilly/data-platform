"""
WerewolfAgent – vai Ma Sói.

Chiến lược (Decision Policy):
  - KHÔNG giết đồng đội (wolf_team)
  - Ưu tiên giết người ÍT bị nghi ngờ nhất (an toàn cho nhóm, khó bị lộ)
  - Ưu tiên giết người HAY DẪN DẮT (nhiều lần bị nhắc tên → ảnh hưởng cao)
  - Ngày: giả vờ vô tội, đổ nghi ngờ sang người khác
  - Bỏ phiếu: loại người nguy hiểm nhất với nhóm Ma Sói

📌 Nâng cấp sau: dùng belief score thay cho random.
"""

import random
from .base_agent import BaseAgent


class WerewolfAgent(BaseAgent):

    def __init__(self, name: str, teammates: list[str] = None):
        super().__init__(name, role="werewolf")
        # wolf_team: danh sách tên đồng đội Ma Sói (KHÔNG bao gồm bản thân)
        self.wolf_team: list[str] = teammates or []

    # ── BELIEF: tin tưởng đồng đội hoàn toàn ─────────────────────────
    def init_belief(self, players: list[str]) -> None:
        super().init_belief(players)
        for t in self.wolf_team:
            if t in self.belief:
                self.belief[t] = 0.0   # đồng đội → không nghi ngờ

    # ── DECIDE (cốt lõi – override abstract method) ───────────────────
    def decide(self, game_state) -> dict:
        """
        Quyết định hành động tùy theo pha hiện tại.

        Phase "night" → chọn mục tiêu giết
        Phase "vote"  → chọn mục tiêu bỏ phiếu
        Phase "day"   → trả về câu phát biểu
        """
        if game_state.phase == "night":
            return self._decide_kill(game_state)
        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            return {"action": "vote", "target": self.vote(candidates)}
        # day
        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    # ── NIGHT: chọn mục tiêu giết ─────────────────────────────────────
    def _decide_kill(self, game_state) -> dict:
        """
        Ưu tiên theo thứ tự:
          1. Người ÍT bị nghi ngờ nhất (belief thấp) → an toàn khi biến mất
          2. Người HAY DẪN DẮT (được nhắc tên nhiều trong memory)
          3. Fallback: random
        """
        # Loại trừ bản thân và đồng đội
        targets = [
            p for p in game_state.alive
            if p != self.name and p not in self.wolf_team
        ]
        if not targets:
            return {"action": "kill", "target": None}

        # Tính điểm "nguy hiểm" cho từng mục tiêu
        # Điểm = influence_score - suspicion_score
        # Cao → nên giết (có ảnh hưởng cao, ít bị nghi → cần loại)
        scores = {}
        for t in targets:
            # influence: số lần tên t xuất hiện trong memory của ta
            influence = sum(
                1 for entry in self.memory
                if t in entry.get("event", "") or t in entry.get("msg", "")
            )
            # suspicion từ góc nhìn Ta (belief của ta về t)
            suspicion = self.belief.get(t, 0.5)
            # Muốn giết người có influence cao VÀ belief thấp (chưa bị nghi bởi dân)
            scores[t] = influence * 0.6 + (1.0 - suspicion) * 0.4

        target = max(targets, key=lambda p: scores[p])

        # Fallback nếu tất cả điểm bằng 0 → random
        if all(v == 0.4 for v in scores.values()):
            target = random.choice(targets)

        self.remember(
            game_state.round,
            f"Ta chon giet {target} (score={scores[target]:.2f}).",
            source="self",
        )
        return {"action": "kill", "target": target}

    # ── DAY: giả vờ vô tội, đổ nghi ─────────────────────────────────
    def discuss(self, game_state) -> str:
        suspects = [
            p for p in game_state.alive
            if p != self.name and p not in self.wolf_team
        ]
        if not suspects:
            return f"{self.name}: Toi khong nghi ngo ai ca."
        # Đổ nghi ngờ lên người bị nghi ngờ nhiều nhất theo belief của ta
        target = self.most_suspected(suspects)
        return (
            f"{self.name}: Toi nghi {target} dang hanh xu rat kha nghi. "
            f"Moi nguoi nen chu y."
        )

    # ── VOTE: loại người nguy hiểm nhất cho nhóm ─────────────────────
    def vote(self, candidates: list[str]) -> str:
        """Loại người có belief cao nhất (dân đang nghi ta nhiều nhất → giết trước)."""
        safe_candidates = [p for p in candidates if p not in self.wolf_team]
        if not safe_candidates:
            return candidates[0]
        return self.most_suspected(safe_candidates)

    # ── Ghi nhận đêm qua ai sống/chết để cập nhật belief ────────────
    def night_action(self, game_state) -> dict:
        """Wrapper gọi decide() cho pha đêm (tương thích GameMaster)."""
        return self._decide_kill(game_state)
