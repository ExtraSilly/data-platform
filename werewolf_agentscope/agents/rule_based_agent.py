"""
RuleBasedAgent – agent dùng luật cứng (heuristic), KHÔNG có BeliefModel.

Mục đích: tầng giữa giữa Random và Belief-based trong thực nghiệm.
  - Có memory đơn giản
  - Belief = dict float thông thường (không dùng BeliefModel 3 chiều)
  - Quyết định theo if/else rule, không có social reasoning
  - Đại diện cho cách tiếp cận truyền thống (rule-based AI)
"""

import random
from .base_agent import BaseAgent


class RuleBasedAgent(BaseAgent):
    """Agent dùng heuristic đơn giản – không có BeliefModel, không có SocialReasoning."""

    def __init__(self, name: str, role: str, teammates: list[str] = None):
        super().__init__(name, role)
        self.teammates: list[str] = teammates or []
        self.checked: dict[str, str] = {}   # chỉ Seer dùng
        self.last_saved: str | None = None  # chỉ Doctor dùng

    # Không dùng BeliefModel – override để dùng dict đơn giản
    def init_belief(self, players: list[str]) -> None:
        self.belief = {p: 0.5 for p in players if p != self.name}
        self._belief_model = None   # tắt BeliefModel

    # ── DECIDE ────────────────────────────────────────────────────────
    def decide(self, game_state) -> dict:
        if game_state.phase == "night":
            return self.night_action(game_state)
        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            return {"action": "vote", "target": self.vote(candidates)}
        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    # ── NIGHT ─────────────────────────────────────────────────────────
    def night_action(self, game_state) -> dict:
        alive = game_state.alive

        if self.role == "werewolf":
            # Rule: chọn ngẫu nhiên trong số không phải đồng đội
            targets = [p for p in alive if p != self.name and p not in self.teammates]
            return {"action": "kill", "target": random.choice(targets) if targets else None}

        if self.role == "doctor":
            # Rule: không cứu người vừa cứu, ưu tiên bản thân nếu bị nghi
            candidates = [p for p in alive if p != self.last_saved]
            if not candidates:
                candidates = list(alive)
            # Rule đơn giản: cứu người bị nghi nhất (belief cao)
            target = max(candidates, key=lambda p: self.belief.get(p, 0.5))
            # Nhưng nếu bị nghi nhiều thì tự cứu
            accusations = sum(1 for e in self.memory
                              if self.name in e.get("event", ""))
            if accusations >= 2 and self.name in candidates:
                target = self.name
            self.last_saved = target
            return {"action": "save", "target": target}

        if self.role == "seer":
            # Rule: check người chưa check, ưu tiên nghi nhất
            unchecked = [p for p in alive if p != self.name and p not in self.checked]
            if not unchecked:
                unchecked = [p for p in alive if p != self.name]
            target = max(unchecked, key=lambda p: self.belief.get(p, 0.5))
            return {"action": "check", "target": target}

        return {"action": "none", "target": None}

    def receive_check_result(self, target: str, result: str, round_num: int) -> None:
        """Seer nhận kết quả – cập nhật belief theo rule cứng."""
        self.checked[target] = result
        self.remember(round_num, f"[CHECK] {target} la {result}.", source="oracle")
        if result == "werewolf":
            self.belief[target] = 1.0
        else:
            self.belief[target] = 0.0

    # ── DAY ───────────────────────────────────────────────────────────
    def discuss(self, game_state) -> str:
        suspects = [p for p in game_state.alive if p != self.name]
        if not suspects:
            return f"{self.name}: Khong co y kien."

        # Rule: tố cáo người có belief cao nhất
        target = max(suspects, key=lambda p: self.belief.get(p, 0.5))

        if self.role == "seer":
            confirmed_wolves = [p for p, r in self.checked.items()
                                if r == "werewolf" and p in game_state.alive]
            if confirmed_wolves:
                return f"{self.name}: Dua tren thong tin, toi nghi {confirmed_wolves[0]}."

        return f"{self.name}: Theo quan sat, {target} co ve kha nghi."

    # ── VOTE ──────────────────────────────────────────────────────────
    def vote(self, candidates: list[str]) -> str:
        # Seer: vote wolf đã xác nhận trước
        if self.role == "seer":
            confirmed = [p for p in candidates if self.checked.get(p) == "werewolf"]
            if confirmed:
                return confirmed[0]
        # Rule: vote người belief cao nhất
        safe = [p for p in candidates if p not in self.teammates]
        if not safe:
            return random.choice(candidates)
        return max(safe, key=lambda p: self.belief.get(p, 0.5))

    # Belief update đơn giản – không dùng BeliefModel
    def update_vote_belief(self, target: str, delta: float) -> None:
        self.update_belief(target, delta)

    def update_speech_belief(self, target: str, delta: float) -> None:
        self.update_belief(target, delta)

    def update_seer_belief(self, target: str, result: str) -> None:
        if result == "werewolf":
            self.belief[target] = 1.0
        else:
            self.belief[target] = 0.0

    def apply_social_reasoning(self, alive: list[str]) -> None:
        pass  # Rule-based không có social reasoning

    def record_vote_round(self, round_num: int, ballots: dict) -> None:
        pass  # không dùng

    def most_suspected(self, candidates=None) -> str:
        pool = candidates if candidates else list(self.belief.keys())
        pool = [p for p in pool if p in self.belief]
        if not pool:
            raise ValueError(f"{self.name}: Khong co ung vien.")
        return max(pool, key=lambda p: self.belief[p])
