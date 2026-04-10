"""
VillagerAgent – vai Dân Thường.

Đặc điểm:
  - KHÔNG biết vai trò của bất kỳ ai
  - Chỉ dựa vào quan sát (memory) để suy luận
  - Vote theo suspicion (belief cao nhất)

Chiến lược cập nhật belief từ memory:
  - Ai đổ nghi ngờ lên người sau đó bị chết → tăng suspicion (có thể là Ma Sói)
  - Ai bị nhiều người nhắc tên → tăng nhẹ suspicion
  - Ai im lặng bất thường → tăng nhẹ suspicion
"""

import random
from .base_agent import BaseAgent


class VillagerAgent(BaseAgent):

    def __init__(self, name: str):
        super().__init__(name, role="villager")

    # ── DECIDE (override abstract) ────────────────────────────────────
    def decide(self, game_state) -> dict:
        """
        Dân thường quyết định dựa hoàn toàn vào belief:
          Phase "night" → không hành động
          Phase "vote"  → vote người suspicious nhất
          Phase "day"   → phát biểu nghi ngờ dựa trên memory
        """
        if game_state.phase == "night":
            return {"action": "none", "target": None}

        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            target = (
                max(self.belief, key=self.belief.get)
                if self.belief
                else random.choice(candidates)
            )
            # Đảm bảo target còn sống và không phải bản thân
            if target not in candidates:
                target = self.most_suspected(candidates)
            return {"action": "vote", "target": target}

        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    # ── DAY: suy luận từ memory ────────────────────────────────────────
    def discuss(self, game_state) -> str:
        """
        Suy luận công khai từ memory:
          1. Ai đổ nghi ngờ lên người cuối cùng bị giết → rất đáng ngờ
          2. Ai xuất hiện nhiều nhất trong memory → đáng ngờ
          3. Fallback: nghi người có belief cao nhất
        """
        suspects = [p for p in game_state.alive if p != self.name]
        if not suspects:
            return f"{self.name}: Khong con ai de nghi ngo."

        # Cập nhật belief từ memory trước khi phán xét
        self._update_belief_from_memory(game_state)

        target = self.most_suspected(suspects)
        evidence = self._find_evidence(target)

        if evidence:
            return f"{self.name}: Toi nghi {target} – {evidence}"
        return f"{self.name}: Nhin lai cac dau hieu, toi cho rang {target} dang nghi ngo nhat."

    # ── Cập nhật belief từ quan sát ──────────────────────────────────
    def _update_belief_from_memory(self, game_state) -> None:
        """
        Phân tích memory để cập nhật suspicion:
          - Ai bị nhắc tên nhiều → tăng suspicion
          - Ai im lặng (ít xuất hiện) khi người khác chết → tăng nhẹ
          - Ai đổ nghi ngờ lên dân thường đã chết → tăng mạnh
        """
        alive = set(game_state.alive)
        dead = set(game_state.dead)

        for p in game_state.alive:
            if p == self.name:
                continue

            # Đếm số lần p bị nhắc trong memory
            mention_count = sum(
                1 for e in self.memory
                if p in e.get("event", "") or p in e.get("msg", "")
            )

            # Đếm số lần p đổ nghi ngờ lên người đã chết (dân thường)
            accusation_score = sum(
                1 for e in self.memory
                if (e.get("source") == p or f"{p}:" in e.get("event", ""))
                and any(d in e.get("event", "") for d in dead)
            )

            # Cập nhật belief
            if mention_count > 0:
                self.update_belief(p, mention_count * 0.03)
            if accusation_score > 0:
                self.update_belief(p, accusation_score * 0.1)

    def _find_evidence(self, target: str) -> str:
        """Tìm bằng chứng cụ thể từ memory về target."""
        evidence_entries = [
            e.get("event") or e.get("msg", "")
            for e in self.recall(last_n=6)
            if target in (e.get("event", "") + e.get("msg", ""))
        ]
        if evidence_entries:
            return evidence_entries[-1]   # bằng chứng gần nhất
        return ""

    # ── Nhận thông tin khi ai đó bị loại ────────────────────────────
    def update_belief_from_accusation(self, accuser: str, accused: str) -> None:
        """
        Khi nghe 'accuser' đổ nghi ngờ lên 'accused':
          - Tăng nhẹ nghi ngờ cả hai (accuser có thể đánh lạc hướng)
        """
        self.update_belief(accuser, +0.05)
        self.update_belief(accused, +0.08)

    # ── VOTE ─────────────────────────────────────────────────────────
    def vote(self, candidates: list[str]) -> str:
        """Vote người có belief cao nhất trong candidates."""
        pool = [p for p in candidates if p in self.belief]
        if not pool:
            return random.choice(candidates)
        return max(pool, key=lambda p: self.belief[p])

    # ── Wrapper tương thích GameMaster ───────────────────────────────
    def night_action(self, game_state) -> dict:
        return {"action": "none", "target": None}
