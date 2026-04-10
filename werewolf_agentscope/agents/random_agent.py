"""
RandomAgent – baseline thuần ngẫu nhiên.

Mục đích: làm baseline so sánh trong thực nghiệm khoa học.
  - Không có belief, không có memory logic
  - Mọi quyết định đều random
  - Giúp trả lời: "Hệ thống AI có tốt hơn random không?"
"""

import random
from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """Agent baseline: hành động hoàn toàn ngẫu nhiên."""

    def __init__(self, name: str, role: str, teammates: list[str] = None):
        super().__init__(name, role)
        self.teammates: list[str] = teammates or []

    def init_belief(self, players: list[str]) -> None:
        # Vẫn khởi tạo belief để tương thích GameMaster
        self.belief = {p: 0.5 for p in players if p != self.name}

    def decide(self, game_state) -> dict:
        if game_state.phase == "night":
            return self.night_action(game_state)
        if game_state.phase == "vote":
            candidates = [p for p in game_state.alive if p != self.name]
            return {"action": "vote", "target": self.vote(candidates)}
        return {"action": "discuss", "target": None, "msg": self.discuss(game_state)}

    def night_action(self, game_state) -> dict:
        alive = game_state.alive
        if self.role == "werewolf":
            targets = [p for p in alive if p != self.name and p not in self.teammates]
            return {"action": "kill", "target": random.choice(targets) if targets else None}
        if self.role == "doctor":
            return {"action": "save", "target": random.choice(alive)}
        if self.role == "seer":
            others = [p for p in alive if p != self.name]
            return {"action": "check", "target": random.choice(others) if others else None}
        return {"action": "none", "target": None}

    def discuss(self, game_state) -> str:
        others = [p for p in game_state.alive if p != self.name]
        if others:
            target = random.choice(others)
            return f"{self.name}: Toi nghi {target} co gi do kha nghi."
        return f"{self.name}: Khong co y kien."

    def vote(self, candidates: list[str]) -> str:
        """Vote hoàn toàn ngẫu nhiên."""
        safe = [p for p in candidates if p not in self.teammates]
        return random.choice(safe) if safe else random.choice(candidates)

    # Seer receive_check_result – giả không dùng
    def receive_check_result(self, target: str, result: str, round_num: int) -> None:
        pass
